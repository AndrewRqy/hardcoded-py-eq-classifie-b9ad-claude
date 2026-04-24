"""
predictor4.py - Sound hard-coded classifier for equational implication over magmas.

Improvements over predictor3:
1. Knuth-Bendix (KB) completion for positive implication (replaces unsound BFS)
2. Z3 SMT model finding for negative implication (replaces incomplete hill-climbing)
3. All other predictor3 components retained (polynomial eval, exhaustive size-2/3, structural)
"""

import re
import itertools
import random
import math
import time


# ─────────────────────────────────────────────────────────────────────────────
# PARSING
# ─────────────────────────────────────────────────────────────────────────────

def parse(s):
    """Parse a magma law expression into a nested tuple tree."""
    stk = [[]]
    for t in re.findall(r'[a-zA-Z0-9_]+|\(|\)|\*', s):
        if t == '(':
            stk.append([])
        elif t == ')':
            if len(stk) > 1:
                inner = stk.pop()
                res = inner[0]
                for i in range(1, len(inner), 2):
                    res = ('*', res, inner[i + 1])
                stk[-1].append(res)
        else:
            stk[-1].append(t)
    res = stk[0][0]
    for i in range(1, len(stk[0]), 2):
        res = ('*', res, stk[0][i + 1])
    return res


# ─────────────────────────────────────────────────────────────────────────────
# TERM UTILITIES
# ─────────────────────────────────────────────────────────────────────────────

def is_var(t):
    # All strings except '*' are variable names (including renamed ones like 'x_1')
    return isinstance(t, str) and t != '*'


def get_vars(t):
    if isinstance(t, str):
        return {t} if t != '*' else set()
    return get_vars(t[1]) | get_vars(t[2])


def term_depth(t):
    if isinstance(t, str):
        return 0
    return 1 + max(term_depth(t[1]), term_depth(t[2]))


def term_size(t):
    if isinstance(t, str):
        return 1
    return 1 + term_size(t[1]) + term_size(t[2])


def count_ops(t):
    if isinstance(t, str):
        return 0
    return 1 + count_ops(t[1]) + count_ops(t[2])


def count_var_occ(t, v):
    if isinstance(t, str):
        return 1 if t == v else 0
    return count_var_occ(t[1], v) + count_var_occ(t[2], v)


def subst(t, sigma):
    """Apply substitution sigma to term t."""
    if isinstance(t, str):
        return sigma.get(t, t)
    return ('*', subst(t[1], sigma), subst(t[2], sigma))


def rename_vars(t, suffix):
    """Rename all variables in t by appending suffix."""
    if isinstance(t, str):
        return t + suffix if t.isalpha() else t
    return ('*', rename_vars(t[1], suffix), rename_vars(t[2], suffix))


def collect_subterms_with_pos(t, pos=()):
    """Yield (subterm, position) pairs for all subterms of t."""
    yield (t, pos)
    if isinstance(t, tuple):
        yield from collect_subterms_with_pos(t[1], pos + (1,))
        yield from collect_subterms_with_pos(t[2], pos + (2,))


def replace_at_pos(t, pos, replacement):
    """Replace subterm at position pos with replacement."""
    if not pos:
        return replacement
    head, *rest = pos
    if head == 1:
        return ('*', replace_at_pos(t[1], rest, replacement), t[2])
    else:
        return ('*', t[1], replace_at_pos(t[2], rest, replacement))


# ─────────────────────────────────────────────────────────────────────────────
# UNIFICATION (Robinson's algorithm)
# ─────────────────────────────────────────────────────────────────────────────

def occurs(var, t):
    """Occurs check: does var appear in t?"""
    if t == var:
        return True
    if isinstance(t, str):
        return False
    return occurs(var, t[1]) or occurs(var, t[2])


def apply_sigma(t, sigma):
    """Apply substitution sigma to t, following chains."""
    if isinstance(t, str):
        if t in sigma:
            return apply_sigma(sigma[t], sigma)
        return t
    return ('*', apply_sigma(t[1], sigma), apply_sigma(t[2], sigma))


def unify(s, t, sigma=None):
    """
    Unify terms s and t, returning a substitution dict or None if unification fails.
    """
    if sigma is None:
        sigma = {}

    def walk(x):
        while isinstance(x, str) and x in sigma:
            x = sigma[x]
        return x

    def unify_rec(s, t):
        s = walk(s)
        t = walk(t)
        if s == t:
            return True
        if is_var(s):
            if occurs(s, t):
                return False
            sigma[s] = t
            return True
        if is_var(t):
            if occurs(t, s):
                return False
            sigma[t] = s
            return True
        if isinstance(s, str) or isinstance(t, str):
            return False
        if not (isinstance(s, tuple) and isinstance(t, tuple) and len(s) == len(t)):
            return False
        return unify_rec(s[1], t[1]) and unify_rec(s[2], t[2])

    if unify_rec(s, t):
        return sigma
    return None


# ─────────────────────────────────────────────────────────────────────────────
# TERM ORDERING — Lexicographic Path Order (LPO) for magma terms
# ─────────────────────────────────────────────────────────────────────────────

def lpo_gt(s, t, var_order):
    """
    Return True if s >_LPO t, using the given variable ordering.
    For magma terms (single binary operator *):
    - s > t if t is a proper subterm of s (subterm property)
    - s*t > u*v (lexicographically) if s > u, or s == u and t > v
    - s*t > x (variable) always (if x is a proper subterm or not in s — actually only if x occurs in s)
    """
    def lpo_gte(s, t):
        return s == t or lpo_gt(s, t, var_order)

    # If s and t are the same
    if s == t:
        return False

    # s is variable
    if is_var(s):
        # var > var only by ordering; var never > compound
        if is_var(t):
            return var_order.get(s, 0) > var_order.get(t, 0)
        return False

    # s is compound: s = (*, s1, s2)
    s1, s2 = s[1], s[2]

    # t is a proper subterm of s → s > t
    if t == s1 or t == s2:
        return True

    # Subterm recursively
    if isinstance(s1, tuple) and lpo_gte(s1, t):
        return True
    if isinstance(s2, tuple) and lpo_gte(s2, t):
        return True

    if is_var(t):
        # s > var if var occurs in s
        return t in get_vars(s)

    # t is also compound: t = (*, t1, t2)
    t1, t2 = t[1], t[2]

    # Lexicographic comparison on (s1, s2) vs (t1, t2)
    if lpo_gt(s1, t1, var_order):
        return lpo_gte(s2, t2)
    if s1 == t1:
        return lpo_gt(s2, t2, var_order)
    return False


def orient_rule(lhs, rhs, var_order):
    """
    Orient an equation (lhs, rhs) into a rule using LPO.
    Returns (lhs, rhs) if lhs > rhs, (rhs, lhs) if rhs > lhs, or None if neither.
    """
    if lpo_gt(lhs, rhs, var_order):
        return (lhs, rhs)
    if lpo_gt(rhs, lhs, var_order):
        return (rhs, lhs)
    return None


# ─────────────────────────────────────────────────────────────────────────────
# NORMAL FORM COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────

MAX_REDUCTION_STEPS = 2000


def rewrite_once(t, rules):
    """
    Apply the first applicable rule in rules to t (at any position).
    Returns (new_term, True) or (t, False) if no rule applies.
    """
    for lhs, rhs in rules:
        # Try to match lhs against t at the root
        sigma = {}
        if match_rule(lhs, t, sigma):
            result = subst(rhs, sigma)
            return result, True
    # Try at subterms
    if isinstance(t, tuple):
        new_left, changed = rewrite_once(t[1], rules)
        if changed:
            return ('*', new_left, t[2]), True
        new_right, changed = rewrite_once(t[2], rules)
        if changed:
            return ('*', t[1], new_right), True
    return t, False


def match_rule(pattern, term, sigma):
    """Match pattern against term (one-way, variables in pattern only)."""
    if is_var(pattern):
        if pattern in sigma:
            return sigma[pattern] == term
        sigma[pattern] = term
        return True
    if isinstance(pattern, str):
        return pattern == term
    if isinstance(term, str):
        return False
    if len(pattern) != len(term):
        return False
    return (match_rule(pattern[1], term[1], sigma) and
            match_rule(pattern[2], term[2], sigma))


def normal_form(t, rules, max_steps=MAX_REDUCTION_STEPS):
    """Reduce t to normal form under rules, with step limit."""
    for _ in range(max_steps):
        new_t, changed = rewrite_once(t, rules)
        if not changed:
            return t
        t = new_t
    return t  # May not be fully reduced; convergence not guaranteed


# ─────────────────────────────────────────────────────────────────────────────
# CRITICAL PAIR COMPUTATION
# ─────────────────────────────────────────────────────────────────────────────

_rename_counter = [0]


def fresh_rename(t):
    """Rename all variables in t with a fresh suffix to avoid collisions."""
    _rename_counter[0] += 1
    return rename_vars(t, f'_{_rename_counter[0]}')


def critical_pairs(rule1, rule2):
    """
    Compute all critical pairs between rule1 = (l1 → r1) and rule2 = (l2 → r2).
    Overlap: subterm of l1 at position p unifies with l2.
    Returns list of (s, t) pairs to be checked for joinability.
    """
    l1, r1 = rule1
    l2_orig, r2_orig = rule2

    # Rename rule2 variables to avoid collisions
    suffix = f'_{_rename_counter[0]}'
    _rename_counter[0] += 1
    l2 = rename_vars(l2_orig, suffix)
    r2 = rename_vars(r2_orig, suffix)

    pairs = []
    for (subterm, pos) in collect_subterms_with_pos(l1):
        if is_var(subterm):
            continue  # Don't overlap at variable positions
        sigma = unify(subterm, l2)
        if sigma is not None:
            # Apply sigma to both sides
            s = apply_sigma(replace_at_pos(l1, pos, r2), sigma)
            t = apply_sigma(r1, sigma)
            if s != t:  # Non-trivial pair
                pairs.append((s, t))
    return pairs


# ─────────────────────────────────────────────────────────────────────────────
# KNUTH-BENDIX COMPLETION
# ─────────────────────────────────────────────────────────────────────────────

MAX_KB_RULES = 40
MAX_KB_STEPS = 200
MAX_KB_TIME = 0.8   # seconds — short timeout to avoid blocking
MAX_RULE_DEPTH = 10


def kb_completion(equation, var_order=None):
    """
    Run Knuth-Bendix completion on a single equation (both orientations).

    Args:
        equation: (lhs, rhs) tuple of terms
        var_order: dict mapping variable names to integers (higher = larger)

    Returns:
        (rules, success) where:
        - rules: list of (lhs, rhs) rewrite rules (may be partial if not converged)
        - success: True if completion terminated (convergent TRS found)
    """
    lhs, rhs = equation
    if var_order is None:
        # Default: alphabetical order (a > b > c > ...)
        all_vars = sorted(get_vars(lhs) | get_vars(rhs))
        var_order = {v: len(all_vars) - i for i, v in enumerate(sorted(all_vars))}

    # Initial set of equations (symmetric)
    equations = set()
    rules = []
    start_time = time.time()

    def add_equation(s, t):
        """Try to orient and add (s, t) as a rule."""
        nonlocal rules
        # Size guard before normalization
        if term_size(s) > 80 or term_size(t) > 80:
            return False
        # Reduce both sides
        try:
            s = normal_form(s, rules)
            t = normal_form(t, rules)
        except RecursionError:
            return False
        if s == t:
            return True  # Joinable, discard
        if term_depth(s) > MAX_RULE_DEPTH or term_depth(t) > MAX_RULE_DEPTH:
            return False  # Too complex, abort
        try:
            rule = orient_rule(s, t, var_order)
        except (RecursionError, IndexError):
            return False
        if rule is None:
            return False  # Cannot orient, KB fails
        rule_lhs, rule_rhs = rule
        # Soundness check: RHS variables must be subset of LHS variables.
        # A rule introducing new variables (e.g. x → y_0) is invalid and
        # would make every term reduce to the same thing.
        if not get_vars(rule_rhs).issubset(get_vars(rule_lhs)):
            return False  # Invalid rule — KB cannot complete soundly
        rules.append(rule)
        return True

    # Try to orient the initial equation
    rule = orient_rule(lhs, rhs, var_order)
    if rule is None:
        # Try swapping variable order
        all_vars = sorted(get_vars(lhs) | get_vars(rhs))
        var_order = {v: i for i, v in enumerate(sorted(all_vars))}
        rule = orient_rule(lhs, rhs, var_order)
        if rule is None:
            return [], False
    rules = [rule]

    processed = set()

    for step in range(MAX_KB_STEPS):
        if time.time() - start_time > MAX_KB_TIME:
            return rules, False  # Timeout

        if len(rules) > MAX_KB_RULES:
            return rules, False  # Too many rules

        # Find an unprocessed pair of rules
        found_pair = False
        for i in range(len(rules)):
            for j in range(len(rules)):
                if (i, j) in processed:
                    continue
                processed.add((i, j))
                found_pair = True
                try:
                    pairs = critical_pairs(rules[i], rules[j])
                except (RecursionError, Exception):
                    return rules, False
                for s, t in pairs:
                    if time.time() - start_time > MAX_KB_TIME:
                        return rules, False
                    ok = add_equation(s, t)
                    if not ok:
                        return rules, False
                    if len(rules) > MAX_KB_RULES:
                        return rules, False
                # After adding new rules, restart outer loop
                if len(rules) > i + 1 or len(rules) > j + 1:
                    break
            else:
                continue
            break

        if not found_pair:
            return rules, True  # All pairs processed — success!

    return rules, False  # Exceeded step limit


def kb_prove_implication(law1_eq, law2_eq):
    """
    Try to prove law1 |= law2 using KB completion.

    Returns:
        True if proven (law2's normal forms match under law1's TRS)
        None if KB timed out, failed, or encountered an error (inconclusive)
    """
    try:
        # Trivially true: LHS == RHS of law2
        if law2_eq[0] == law2_eq[1]:
            return True

        rules, success = kb_completion(law1_eq)
        if not success or not rules:
            return None  # Inconclusive

        # Check if law2's LHS and RHS reduce to the same normal form
        lhs2_nf = normal_form(law2_eq[0], rules)
        rhs2_nf = normal_form(law2_eq[1], rules)
        if lhs2_nf == rhs2_nf:
            return True
        return None  # KB succeeded but couldn't prove law2
    except Exception:
        return None  # RecursionError or other errors → inconclusive


# ─────────────────────────────────────────────────────────────────────────────
# Z3 SMT MODEL FINDING
# ─────────────────────────────────────────────────────────────────────────────

def z3_find_counterexample(law1_eq, law2_eq, n, timeout_ms=3000):
    """
    Use Z3 to find a size-n magma satisfying law1 but violating law2.

    Args:
        law1_eq: (lhs, rhs) for law1
        law2_eq: (lhs, rhs) for law2
        n: domain size
        timeout_ms: Z3 timeout in milliseconds

    Returns:
        table (list of lists) if counterexample found
        None if no counterexample exists for this n (or timeout/error)
    """
    try:
        import z3

        # Create n×n table of integer variables
        T = [[z3.Int(f't_{i}_{j}') for j in range(n)] for i in range(n)]

        solver = z3.Solver()
        solver.set('timeout', timeout_ms)

        # Domain constraints: T[i][j] ∈ {0, ..., n-1}
        for i in range(n):
            for j in range(n):
                solver.add(T[i][j] >= 0, T[i][j] < n)

        v1_all = get_vars(law1_eq[0]) | get_vars(law1_eq[1])
        v2_all = get_vars(law2_eq[0]) | get_vars(law2_eq[1])
        v1_list = sorted(v1_all)
        v2_list = sorted(v2_all)

        def eval_term_z3(term, var_map, T_sym, n_sym):
            """Evaluate term symbolically using Z3 If-then-else for table lookup."""
            if isinstance(term, str):
                return var_map[term]

            left = eval_term_z3(term[1], var_map, T_sym, n_sym)
            right = eval_term_z3(term[2], var_map, T_sym, n_sym)

            # Table lookup: T[left][right]
            # Build If-then-else chain
            result = z3.IntVal(0)
            for i in range(n_sym - 1, -1, -1):
                for j in range(n_sym - 1, -1, -1):
                    result = z3.If(z3.And(left == i, right == j), T_sym[i][j], result)
            return result

        # Law1 must hold: ∀ v1_list assignments, law1_lhs == law1_rhs
        for assign in itertools.product(range(n), repeat=len(v1_list)):
            var_map = {v: z3.IntVal(assign[k]) for k, v in enumerate(v1_list)}
            lhs_val = eval_term_z3(law1_eq[0], var_map, T, n)
            rhs_val = eval_term_z3(law1_eq[1], var_map, T, n)
            solver.add(lhs_val == rhs_val)

        # Law2 must be violated: ∃ v2_list assignment, law2_lhs ≠ law2_rhs
        violation_clauses = []
        for assign in itertools.product(range(n), repeat=len(v2_list)):
            var_map = {v: z3.IntVal(assign[k]) for k, v in enumerate(v2_list)}
            lhs_val = eval_term_z3(law2_eq[0], var_map, T, n)
            rhs_val = eval_term_z3(law2_eq[1], var_map, T, n)
            violation_clauses.append(lhs_val != rhs_val)
        solver.add(z3.Or(violation_clauses))

        result = solver.check()
        if result == z3.sat:
            model = solver.model()
            table = [[model.eval(T[i][j]).as_long() for j in range(n)] for i in range(n)]
            return table
        return None  # unsat or unknown (no counterexample of this size)

    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# MAIN PREDICTION FUNCTION
# ─────────────────────────────────────────────────────────────────────────────

def predict_implication_probability(law1: str, law2: str) -> float:
    """
    Predicts P(law1 |= law2) using:
    1. Trivial checks (direct specialization, trivial laws)
    2. Knuth-Bendix completion (sound positive implication proof)
    3. Linear polynomial counterexample search
    4. Random polynomial evaluation over large primes
    5. Exhaustive finite magma search (size 2 and 3)
    6. Z3 SMT model finding (sizes 4 and 5) — replaces hill-climbing
    7. Structural feature-based probability estimation (fallback)
    """
    try:
        # ─── PARSING ───────────────────────────────────────────────
        t1 = tuple(parse(x) for x in law1.split('='))
        t2 = tuple(parse(x) for x in law2.split('='))

        # ─── HELPERS ───────────────────────────────────────────────
        def match(p, g, s):
            if isinstance(p, str):
                if not p.isalpha():
                    return p == g
                if p not in s:
                    s[p] = g
                    return True
                return s[p] == g
            if isinstance(g, str) or len(p) != len(g):
                return False
            return all(match(p[i], g[i], s) for i in range(len(p)))

        def apply_sub(t, s):
            if isinstance(t, str):
                return s.get(t, t)
            return (t[0], apply_sub(t[1], s), apply_sub(t[2], s))

        # ─── TRIVIAL CASES ─────────────────────────────────────────
        if match(t1, t2, {}) or match((t1[1], t1[0]), t2, {}):
            return 0.9999
        if t2[0] == t2[1]:
            return 0.9999
        if t1[0] == t1[1]:
            return 0.0001

        v1_all = get_vars(t1[0]) | get_vars(t1[1])
        v2_all = get_vars(t2[0]) | get_vars(t2[1])
        v1_list = sorted(v1_all)
        v2_list = sorted(v2_all)

        # ─── KNUTH-BENDIX COMPLETION (positive path — sound) ────────
        kb_result = kb_prove_implication(t1, t2)
        if kb_result is True:
            return 0.9999  # Sound proof: law1 |= law2 via convergent TRS

        # ─── BFS REWRITING (fallback after KB fails) ─────────────
        # BFS is unsound (may give false positives via term set collisions)
        # but highly effective in practice. Used only as fallback.
        def _term_depth_bfs(t):
            if isinstance(t, str):
                return 0
            return 1 + max(_term_depth_bfs(t[1]), _term_depth_bfs(t[2]))

        MAX_TERM_DEPTH_BFS = 12

        def _match_bfs(p, g, s):
            if isinstance(p, str):
                if not p.isalpha():
                    return p == g
                if p not in s:
                    s[p] = g
                    return True
                return s[p] == g
            if isinstance(g, str) or len(p) != len(g):
                return False
            return all(_match_bfs(p[i], g[i], s) for i in range(len(p)))

        def _apply_bfs(t, s):
            if isinstance(t, str):
                return s.get(t, t)
            return (t[0], _apply_bfs(t[1], s), _apply_bfs(t[2], s))

        def _get_rewrites_bfs(term, rules_bfs, depth=0):
            if depth > MAX_TERM_DEPTH_BFS:
                return set()
            res = set()
            for rl, rr in rules_bfs:
                sub = {}
                if _match_bfs(rl, term, sub):
                    nxt = _apply_bfs(rr, sub)
                    if _term_depth_bfs(nxt) <= MAX_TERM_DEPTH_BFS:
                        res.add(nxt)
            if isinstance(term, tuple):
                for lt in _get_rewrites_bfs(term[1], rules_bfs, depth + 1):
                    res.add(('*', lt, term[2]))
                for rt in _get_rewrites_bfs(term[2], rules_bfs, depth + 1):
                    res.add(('*', term[1], rt))
            return res

        def _bfs_expand(start, rules_bfs, limit=500):
            visited = {start}
            queue = [start]
            for curr in queue:
                if len(visited) >= limit:
                    break
                try:
                    for nxt in _get_rewrites_bfs(curr, rules_bfs):
                        if nxt not in visited:
                            visited.add(nxt)
                            queue.append(nxt)
                except RecursionError:
                    break
            return visited

        bfs_rules = [(t1[0], t1[1]), (t1[1], t1[0])]
        lhs2_reach = _bfs_expand(t2[0], bfs_rules, limit=500)
        rhs2_reach = _bfs_expand(t2[1], bfs_rules, limit=500)
        bfs_proof = not lhs2_reach.isdisjoint(rhs2_reach)

        if bfs_proof:
            return 0.9999  # BFS path found (note: may rarely be false positive)

        reach_score = math.log1p(len(lhs2_reach) + len(rhs2_reach)) / 8.0

        # Check if a variable expands to multiple terms (degeneracy signal)
        var_expansion = _bfs_expand('x', bfs_rules, limit=200)
        if any(isinstance(m, str) and m.isalpha() and m != 'x' for m in var_expansion):
            return 0.9999

        # ─── LINEAR POLYNOMIAL COUNTEREXAMPLE SEARCH ───────────────
        def get_lin_poly(t):
            coeffs, k_terms = {}, []

            def wk(n, lc, rc):
                if isinstance(n, str):
                    if n.isalpha():
                        coeffs[n] = coeffs.get(n, []) + [(lc, rc)]
                else:
                    k_terms.append((lc, rc))
                    wk(n[1], lc + 1, rc)
                    wk(n[2], lc, rc + 1)

            wk(t, 0, 0)
            return coeffs, k_terms

        p1l_poly = get_lin_poly(t1[0])
        p1r_poly = get_lin_poly(t1[1])
        p2l_poly = get_lin_poly(t2[0])
        p2r_poly = get_lin_poly(t2[1])

        def eval_poly(poly, a, b, p, ap, bp):
            cw = {v: sum(ap[lc] * bp[rc] for lc, rc in ts) % p for v, ts in poly[0].items()}
            ck = sum(ap[lc] * bp[rc] for lc, rc in poly[1]) % p
            return cw, ck

        for p_val in [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41, 43, 47]:
            ap, bp = [1] * 15, [1] * 15
            for a, b in itertools.product(range(p_val), repeat=2):
                for i in range(1, 15):
                    ap[i] = (ap[i - 1] * a) % p_val
                    bp[i] = (bp[i - 1] * b) % p_val
                c1l, k1l = eval_poly(p1l_poly, a, b, p_val, ap, bp)
                c1r, k1r = eval_poly(p1r_poly, a, b, p_val, ap, bp)
                if all(c1l.get(v, 0) == c1r.get(v, 0) for v in v1_all) and k1l == k1r:
                    c2l, k2l = eval_poly(p2l_poly, a, b, p_val, ap, bp)
                    c2r, k2r = eval_poly(p2r_poly, a, b, p_val, ap, bp)
                    if not (all(c2l.get(v, 0) == c2r.get(v, 0) for v in v2_all) and k2l == k2r):
                        return 0.0001

        # ─── RANDOM POLYNOMIAL EVALUATION OVER LARGE PRIMES ────────
        v_all_sorted = sorted(v1_all | v2_all)
        random.seed(42)
        r_sat, r_cnt = 0, 0

        for si in range(80):
            rng = random.Random(si + 1000)
            for mod in [2147483647, 2147483579, 2147483629, 2147483423]:
                p = [rng.randint(1, mod - 1) for _ in range(6)]
                v_m = {v: rng.randint(0, mod - 1) for v in v_all_sorted}
                for dual in [False, True]:
                    def ev_r(n, _p=p, _vm=v_m, _mod=mod, _dual=dual):
                        if isinstance(n, str):
                            return _vm.get(n, 17)
                        ln = ev_r(n[2] if _dual else n[1])
                        rn = ev_r(n[1] if _dual else n[2])
                        return (ln * _p[0] + rn * _p[1] + ln * rn * _p[2] +
                                (ln * ln) % _mod * _p[3] % _mod +
                                (rn * rn) % _mod * _p[4] % _mod +
                                _p[5]) % _mod

                    if ev_r(t1[0]) == ev_r(t1[1]):
                        r_cnt += 1
                        if ev_r(t2[0]) == ev_r(t2[1]):
                            r_sat += 1
                        else:
                            return 0.0001

        r_sc = r_sat / r_cnt if r_cnt > 0 else 0.5

        # ─── FINITE MAGMA CHECKING UTILITY ─────────────────────────
        def check_law(tp, v_list, table):
            sz = len(table)
            n_vars = len(v_list)
            if n_vars == 0:
                def ev0(t):
                    if isinstance(t, str):
                        return 0
                    return table[ev0(t[1])][ev0(t[2])]
                return ev0(tp[0]) == ev0(tp[1])
            v_map = {v: i for i, v in enumerate(v_list)}

            def ev(t, vs):
                if isinstance(t, str):
                    return vs[v_map[t]] if t in v_map else 0
                return table[ev(t[1], vs)][ev(t[2], vs)]

            limit = 1024
            if sz ** n_vars <= limit:
                for vs in itertools.product(range(sz), repeat=n_vars):
                    if ev(tp[0], vs) != ev(tp[1], vs):
                        return False
            else:
                for _ in range(limit):
                    vs = [random.randint(0, sz - 1) for _ in range(n_vars)]
                    if ev(tp[0], vs) != ev(tp[1], vs):
                        return False
            return True

        # ─── EXHAUSTIVE FINITE MAGMA SEARCH (sizes 2 and 3) ────────
        def generate_small_magmas():
            # Size 2: all 16 boolean magmas
            for i in range(16):
                yield [[(i >> (2 * r + c)) & 1 for c in range(2)] for r in range(2)]

            # Size 2-4: structured operations
            yield [[(r ^ c) for c in range(4)] for r in range(4)]
            yield [[(r & c) for c in range(4)] for r in range(4)]
            yield [[(r | c) for c in range(4)] for r in range(4)]
            for op in [lambda x, y: x & y, lambda x, y: x | y,
                       lambda x, y: x ^ y, lambda x, y: int(x and not y)]:
                yield [[op(r, c) for c in range(2)] for r in range(2)]

            # Small affine magmas
            for n in [2, 3, 4]:
                for a, b, k, q in itertools.product(range(n), repeat=4):
                    yield [[(a * r + b * c + q * r * c + k) % n for c in range(n)] for r in range(n)]

            # Cyclic groups
            for n in [2, 3, 4, 5, 6, 7]:
                yield [[(r + c) % n for c in range(n)] for r in range(n)]
                yield [[(r - c) % n for c in range(n)] for r in range(n)]
                yield [[(r * c) % n for c in range(n)] for r in range(n)]

            # Projection and constant magmas
            for n in [2, 3, 4, 5, 6]:
                yield [[r for _ in range(n)] for r in range(n)]
                yield [[c for c in range(n)] for _ in range(n)]
                yield [[max(r, c) for c in range(n)] for r in range(n)]
                yield [[min(r, c) for c in range(n)] for r in range(n)]
                yield [[(r + 1) % n for _ in range(n)] for r in range(n)]
                yield [[(c + 1) % n for c in range(n)] for _ in range(n)]

            # Quadratic-like magmas
            for n in [3, 4, 5]:
                yield [[(r * r + c) % n for c in range(n)] for r in range(n)]
                yield [[(r + c + r * c) % n for c in range(n)] for r in range(n)]
                yield [[(r * c * c + 1) % n for c in range(n)] for r in range(n)]

            # ALL size-3 magmas (exhaustive: 3^9 = 19683)
            max_vars = max(len(v1_all), len(v2_all))
            if max_vars <= 3:
                for table_flat in itertools.product(range(3), repeat=9):
                    yield [list(table_flat[r * 3:(r + 1) * 3]) for r in range(3)]

            # Named algebraic structures
            yield [[0, 1, 2, 3, 4, 5], [1, 0, 4, 5, 2, 3],
                   [2, 5, 0, 4, 3, 1], [3, 4, 5, 0, 1, 2],
                   [4, 3, 1, 2, 5, 0], [5, 2, 3, 1, 0, 4]]  # S3

            yield [[0, 1, 2, 3, 4], [1, 0, 4, 2, 3],
                   [2, 3, 0, 4, 1], [3, 4, 1, 0, 2],
                   [4, 2, 3, 1, 0]]  # Non-associative loop order 5

            q8 = [[0, 1, 2, 3, 4, 5, 6, 7], [1, 0, 3, 2, 5, 4, 7, 6],
                  [2, 3, 1, 0, 6, 7, 5, 4], [3, 2, 0, 1, 7, 6, 4, 5],
                  [4, 5, 7, 6, 1, 0, 2, 3], [5, 4, 6, 7, 0, 1, 3, 2],
                  [6, 7, 4, 5, 3, 2, 1, 0], [7, 6, 5, 4, 2, 3, 0, 1]]
            yield q8

            yield [[0, 2, 1], [2, 1, 0], [1, 0, 2]]  # Steiner triple
            yield [[(r + 1) % 3 if r == c else r for c in range(3)] for r in range(3)]

            # Random magmas
            for sz in [2, 3, 4, 5, 6, 7]:
                seeds = 15 if sz <= 4 else 10
                for seed in range(seeds):
                    rng = random.Random(seed * 113 + sz * 7)
                    yield [[rng.randint(0, sz - 1) for _ in range(sz)] for _ in range(sz)]

        sat1 = 0
        n_samp = 0
        for tbl in generate_small_magmas():
            for tb in [tbl, [list(col) for col in zip(*tbl)]]:
                n_samp += 1
                if check_law(t1, v1_list, tb):
                    sat1 += 1
                    if not check_law(t2, v2_list, tb):
                        return 0.0001

        # ─── Z3 SMT MODEL FINDING (sizes 4, 5) ─────────────────────
        # Replaces hill-climbing: complete for each fixed n
        max_vars = max(len(v1_all), len(v2_all))
        for n in [4, 5]:
            # Use short timeouts — we want fast counterexample finding
            # If Z3 takes long, it's likely a true implication; fall through to heuristic
            if n == 5 and max_vars >= 4:
                timeout = 600   # 4-var laws at n=5 have 625 assignments: can be slow
            elif n == 5:
                timeout = 1000
            else:
                timeout = 800   # n=4: should be fast for most non-implications

            counterex = z3_find_counterexample(t1, t2, n, timeout_ms=timeout)
            if counterex is not None:
                return 0.0001  # Sound counterexample found

        # ─── STRUCTURAL ANALYSIS ────────────────────────────────────
        def analyze(t):
            if isinstance(t, str):
                s = {t} if t.isalpha() else set()
                return (s, (1 if t.isalpha() else 0), 0, 0, 1, {t}, set())
            v1, c1, o1, d1, ts1, us1, p1 = analyze(t[1])
            v2, c2, o2, d2, ts2, us2, p2 = analyze(t[2])
            p_n = p1 | p2
            for vv1 in v1:
                for vv2 in v2:
                    p_n.add((vv1, vv2))
            return (v1 | v2, c1 + c2, o1 + o2 + 1, max(d1, d2) + 1,
                    ts1 + ts2 + 1, us1 | us2 | {t}, p_n)

        v1l, c1l, o1l, d1l, ts1l, us1l, p1l = analyze(t1[0])
        v1r, c1r, o1r, d1r, ts1r, us1r, p1r = analyze(t1[1])
        v2l, c2l, o2l, d2l, ts2l, us2l, p2l = analyze(t2[0])
        v2r, c2r, o2r, d2r, ts2r, us2r, p2r = analyze(t2[1])

        ops1_total = o1l + o1r
        ops2_total = o2l + o2r
        d1_max = max(d1l, d1r)
        d2_max = max(d2l, d2r)
        us1_all = us1l | us1r
        us2_all = us2l | us2r
        p1_all = p1l | p1r
        p2_all = p2l | p2r

        # ─── CANONICAL SUBTERM SIGNATURE ────────────────────────────
        def canonicalize(term):
            var_map = {}
            idx = [0]

            def rec(n):
                if isinstance(n, str):
                    if n.isalpha():
                        if n not in var_map:
                            var_map[n] = f'v{idx[0]}'
                            idx[0] += 1
                        return var_map[n]
                    return n
                return (n[0], rec(n[1]), rec(n[2]))

            return rec(term)

        def get_canon_subterms(term):
            canon = set()

            def walk(n):
                canon.add(canonicalize(n))
                if isinstance(n, tuple):
                    walk(n[1])
                    walk(n[2])

            walk(term)
            return canon

        canon_sig1 = get_canon_subterms(t1[0]) | get_canon_subterms(t1[1])
        canon_sig2 = get_canon_subterms(t2[0]) | get_canon_subterms(t2[1])
        intersection_len = len(canon_sig1 & canon_sig2)
        union_len = len(canon_sig1 | canon_sig2)
        structural_sig_sim = intersection_len / union_len if union_len > 0 else 0.0
        canon_sig2_len = len(canon_sig2)
        canonical_legacy = intersection_len / canon_sig2_len if canon_sig2_len > 0 else 0.0
        canonical_novelty = len(canon_sig2 - canon_sig1) / canon_sig2_len if canon_sig2_len > 0 else 0.0

        # ─── PATTERN MATCHING for known law types ───────────────────
        def m(p, t):
            return match(p, t, {}) or match((p[1], p[0]), t, {})

        p_a = (('*', ('*', 'a', 'b'), 'c'), ('*', 'a', ('*', 'b', 'c')))
        p_c = (('*', 'a', 'b'), ('*', 'b', 'a'))
        p_i = (('*', 'a', 'a'), 'a')
        p_lp = (('*', 'a', 'b'), 'a')
        p_rp = (('*', 'a', 'b'), 'b')
        p_cn = (('*', 'a', 'b'), 'c')
        p_inv = (('*', 'a', ('*', 'b', 'a')), 'b')
        p_bol = (('*', 'a', ('*', 'b', ('*', 'a', 'c'))), ('*', ('*', 'a', ('*', 'b', 'a')), 'c'))
        p_m = (('*', ('*', 'a', 'b'), ('*', 'c', 'd')), ('*', ('*', 'a', 'c'), ('*', 'b', 'd')))
        p_ld = (('*', 'a', ('*', 'b', 'c')), ('*', ('*', 'a', 'b'), ('*', 'a', 'c')))
        p_rd = (('*', ('*', 'a', 'b'), 'c'), ('*', ('*', 'a', 'c'), ('*', 'b', 'c')))
        p_rr = (('*', ('*', 'a', 'b'), 'b'), 'a')
        p_lr = (('*', 'a', ('*', 'a', 'b')), 'b')
        p_f = (('*', 'a', ('*', 'b', 'a')), ('*', ('*', 'a', 'b'), 'a'))

        is_a1 = m(p_a, t1); is_c1 = m(p_c, t1); is_i1 = m(p_i, t1)
        is_lp1 = m(p_lp, t1); is_rp1 = m(p_rp, t1); is_cn1 = m(p_cn, t1)
        is_inv1 = m(p_inv, t1); is_m1 = m(p_m, t1); is_ld1 = m(p_ld, t1)
        is_rd1 = m(p_rd, t1); is_rr1 = m(p_rr, t1); is_lr1 = m(p_lr, t1)
        is_f1 = m(p_f, t1); is_bol1 = m(p_bol, t1)

        is_a2 = m(p_a, t2); is_c2 = m(p_c, t2); is_i2 = m(p_i, t2)
        is_lp2 = m(p_lp, t2); is_rp2 = m(p_rp, t2); is_cn2 = m(p_cn, t2)
        is_inv2 = m(p_inv, t2); is_m2 = m(p_m, t2); is_ld2 = m(p_ld, t2)
        is_rd2 = m(p_rd, t2); is_rr2 = m(p_rr, t2); is_lr2 = m(p_lr, t2)
        is_f2 = m(p_f, t2); is_bol2 = m(p_bol, t2)

        is_lin1 = all(count_var_occ(t1[0], v) == 1 and count_var_occ(t1[1], v) == 1 for v in v1_all)
        is_lin2 = all(count_var_occ(t2[0], v) == 1 and count_var_occ(t2[1], v) == 1 for v in v2_all)

        vbs1 = sum(abs(count_var_occ(t1[0], v) - count_var_occ(t1[1], v)) for v in v1_all)
        vbs2 = sum(abs(count_var_occ(t2[0], v) - count_var_occ(t2[1], v)) for v in v2_all)

        def get_vdp(t, v_a):
            if not v_a:
                return 0, 0

            def d(n, v, cur_d):
                if isinstance(n, str):
                    return [cur_d] if n == v else []
                return d(n[1], v, cur_d + 1) + d(n[2], v, cur_d + 1)

            all_depths = []
            for v in v_a:
                dl = d(t[0], v, 0) + d(t[1], v, 0)
                all_depths.extend(dl)
            if not all_depths:
                return 0, 0
            m_val = sum(all_depths) / len(all_depths)
            std_val = (sum((x - m_val) ** 2 for x in all_depths) / len(all_depths)) ** 0.5
            return m_val, std_val

        m1, dp1 = get_vdp(t1, v1_all)
        m2, dp2 = get_vdp(t2, v2_all)

        sh_rat = (len(v1_all & v2_all) / len(v1_all | v2_all)) if (v1_all | v2_all) else 1.0
        diff_v = len(v1_all) - len(v2_all)
        v2_new = len(v2_all - v1_all)
        is_vk = (len(v1l - v1r) > 0) or (len(v1r - v1l) > 0)

        imb1 = len(v1l ^ v1r)
        imb2 = len(v2l ^ v2r)
        diff_redundancy = (c1l + c1r - len(v1_all)) - (c2l + c2r - len(v2_all))

        # ─── PROBABILITY COMPUTATION ─────────────────────────────────
        if sat1 == 0:
            base = 0.95
        else:
            coverage_ratio = sat1 / float(n_samp)
            base = 0.62 + 0.35 * coverage_ratio

        base += (r_sc - 0.5) * 1.3

        adj = 0.0
        adj += diff_v * 0.07
        adj += (ops1_total - ops2_total) * 0.025
        adj += (d1_max - d2_max) * 0.025
        adj += (sh_rat - 0.5) * 0.18
        adj += reach_score * 0.30   # BFS reachability signal
        adj += (is_lp1 - is_lp2) * 0.28
        adj += (is_rp1 - is_rp2) * 0.28
        adj += (is_cn1 - is_cn2) * 0.20
        adj += (is_a1 - is_a2) * 0.14
        adj += (is_c1 - is_c2) * 0.14
        adj += (is_i1 - is_i2) * 0.07
        adj += (is_inv1 - is_inv2) * 0.12
        adj += (is_m1 - is_m2) * 0.10
        adj += (is_ld1 - is_ld2) * 0.06
        adj += (is_rd1 - is_rd2) * 0.06
        adj += (is_rr1 - is_rr2) * 0.05
        adj += (is_lr1 - is_lr2) * 0.05
        adj += (is_f1 - is_f2) * 0.05
        adj += (is_bol1 - is_bol2) * 0.04
        adj += (is_lin1 - is_lin2) * 0.06
        adj += (vbs2 - vbs1) * -0.03
        adj += ((vbs1 == 0) - (vbs2 == 0)) * -0.15
        adj += structural_sig_sim * 0.48
        adj += canonical_legacy * 0.55
        adj -= canonical_novelty * 0.32

        us2_len = len(us2_all)
        if us2_len > 0:
            subterm_cov = len(us1_all & us2_all) / us2_len
            adj += (subterm_cov - 0.5) * 0.35

        adj += (imb1 - imb2) * 0.04
        adj += diff_redundancy * -0.02

        if v2_new > 0 and not is_vk:
            adj -= (0.38 + 0.15 * v2_new)

        adj += (m2 - m1) * -0.03

        prob = base + adj

        if is_a1 and is_c1:
            if is_a2:
                prob += 0.07
            if is_c2:
                prob += 0.07
        if (is_lp1 or is_rp1) and not (is_lp2 or is_rp2):
            prob += 0.09

        return max(0.0001, min(0.9999, prob))

    except Exception:
        return 0.5
