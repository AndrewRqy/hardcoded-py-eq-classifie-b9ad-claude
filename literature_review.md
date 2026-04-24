# Literature Review: Advanced Hard-Coded Python Classifier for Equation Theory

## Research Area Overview

This project targets the **equational implication problem over magmas**: given equational laws `law1` and `law2` over a single binary operation `*`, determine whether every magma satisfying `law1` also satisfies `law2`. Formally, `law1 |= law2` iff for all magmas M: `M |= law1 ⟹ M |= law2`.

The **Equational Theories Project (ETP)** established the complete ground truth: 4,694 equational laws of order ≤ 4 (at most 4 applications of `*`) with all 22,028,942 pairwise implications determined and verified in Lean. The hypothesis for this project is that replacing BFS term rewriting (positive implication) and hill-climbing search (negative implication) in predictor3 with **Knuth-Bendix (KB) completion** and **SMT model finding (Z3)**, respectively, will increase soundness and accuracy.

---

## Key Definitions

**Definition (Magma):** A set M with a binary operation `◇: M × M → M` (no other axioms).

**Definition (Equational Law):** An identity `L = R` where L, R are terms over variables and `◇`. E.g., `x * (y * z) = (x * y) * z` (associativity).

**Definition (Implication):** `E |= E'` iff every magma satisfying `E` also satisfies `E'`. The relation is a preorder; `x = y` (singleton) is minimum and `x = x` (trivial) is maximum.

**Definition (Term Rewrite System, TRS):** A set of directed equations `ℓ → r` used for rewriting terms. A TRS R is:
- **Terminating**: no infinite rewrite sequences exist
- **Confluent**: all terms have a unique normal form
- **Convergent**: both terminating and confluent

**Definition (Knuth-Bendix Completion):** An algorithm that takes an equational system E and a reduction order `>` and attempts to transform E into an equivalent convergent TRS R. When successful, R is a decision procedure for the word problem: `s ↔*_E t` iff the R-normal forms of s and t coincide.

**Definition (Critical Pair):** For two rules `ℓ₁ → r₁` and `ℓ₂ → r₂` in R (with disjoint variables), if some subterm of `ℓ₁` unifies with `ℓ₂` via unifier σ, then `(r₁σ, ℓ₁σ[r₂σ]_p)` is a critical pair. R is locally confluent iff all critical pairs are joinable (Huet 1980).

**Definition (Lexicographic Path Order, LPO):** A reduction order on terms. `s >_LPO t` if `s` is structurally larger than `t` according to a precedence on function symbols. For magma terms with a single `*`, LPO reduces to a variable-based ordering. Used to orient equations in KB completion.

**Definition (SMT Finite Model Finding):** Using an SMT solver (e.g., Z3) to decide if there exists a finite algebraic structure (here: a magma of size n) satisfying given equational constraints. The magma table `T[i][j] ∈ {0,...,n-1}` is encoded as integer variables; law evaluation uses If-then-else chains for symbolic table lookup.

**Definition (Ground Truth Encoding):** In `raw_implications.csv`, each entry is an integer: `+3`/`+4` = proven implication (by two different proof methods), `-3`/`-4` = proven non-implication.

---

## Key Papers

### Paper 1: The Equational Theories Project (ETP)

- **Authors**: Matthew Bolan, Joachim Breitner, et al. (including Terence Tao, Mario Carneiro)
- **Year**: December 2025 (arXiv:2512.07087v2)

**Main Results:**
- Complete determination of all 22,028,942 pairwise implications among 4,694 equational laws of order ≤ 4, verified in Lean 4.
- 8,178,279 positive implications (37.1%); 13,855,357 non-implications (62.9%).
- 4,694 laws form 1,415 equivalence classes; 1,496 laws are equivalent to the singleton law (E2).
- CNN baseline (5-layer 1D CNN, character tokenization): **99.7% accuracy** on full 22M matrix.

**Proof Automation Techniques (Section 7):**
- **Automated Theorem Provers**: Vampire, Prover9 (superposition/saturation), Duper.
- **Equational Reasoning**: MagmaEgg (ATP for magmas using the egg e-graph library).
- **Counterexample Search**: Mace4 (finite model finder), searching magmas of size ≤ 6–8.
- **SMT**: Z3 used for some implications, confirming Z3's applicability to this domain.

**Relevance to Our Research:** Ground truth source; defines evaluation methodology (log-loss on full 22M matrix); confirms Z3 and finite magma search are state-of-the-art for this problem.

---

### Paper 2: Recording Completion for Finding and Certifying Proofs in Equational Logic

- **Authors**: Thomas Sternagel, René Thiemann, Harald Zankl, Christian Sternagel
- **Year**: 2012 (arXiv:1208.1597v1)
- **File**: `papers/recording_completion_equational_logic_Sternagel2012.pdf`

**Main Results:**
- Introduces *recording completion*: KB completion extended with a history component H that records how each rule in R was derived from E.
- From a join `s →*_R ·*_R← t`, the recall phase reconstructs a conversion `s ↔*_E t`, providing explicit proofs.
- **Theorem 1**: Every successful run of recording completion is sound (R is convergent and equivalent to E).
- **Theorem 2**: A TRS over `T(F, String)` is locally confluent iff all critical pairs are joinable.
- Implemented in IsaFoR/CeTA (certified completion). KBCV and MKBTT are tools that produce certifiable KB proofs.
- Inference rules: deduce, orientl, orientr, simplifyl, simplifyr, delete, compose, collapse.

**Key Technical Insight:** For finite KB runs (the only case relevant to our bounded search), the strict encompassment condition in the collapse rule is not required. This simplifies implementation.

**Relevance to Our Research:** Core reference for the KB completion implementation. The three-phase structure (record → compare → recall) directly maps to our use case: run KB on `law1`, check if `law2`'s LHS and RHS have the same R-normal form. We do not need the recall (proof reconstruction) phase — only the record (convergent TRS construction) and compare (normal form check) phases.

---

### Paper 3: Equational Theories and Validity for Logically Constrained Term Rewriting (Full Version)

- **Year**: 2024 (arXiv:2405.01174v3)
- **File**: `papers/equational_theories_validity_constrained_rewriting_2024.pdf`

**Main Results:**
- Extends equational validity to logically constrained TRS (rules equipped with side conditions from an arbitrary theory).
- Provides decision procedures for equational validity in constrained rewriting: reduces to SMT queries.
- Establishes connection between equational theories and constraint satisfaction.

**Relevance to Our Research:** Background on the SMT-equational theory interface. Confirms that SMT-based model finding is theoretically grounded for equational implication checking.

---

## Known Results (Prerequisite Theorems)

**Theorem (Birkhoff Completeness, 1935):** `E |= E'` iff there is an equational derivation from E proving E'. For term rewriting: `E |= (s = t)` iff `s ↔*_E t` (the two sides are connected by a finite sequence of equational rewrites).

**Implication for KB:** When KB completion of E terminates with convergent TRS R, `E |= (s = t)` iff `NF_R(s) = NF_R(t)` (their R-normal forms are equal). This is a **complete decision procedure** for the word problem relative to E.

**Theorem (Knuth-Bendix Completion, 1970):** Given an equational system E and a reduction order `>`, KB completion either:
1. Succeeds: produces a convergent TRS R equivalent to E (then R decides `s ↔*_E t`), or
2. Fails: produces a non-orientable equation (indicates the procedure failed with this order), or
3. Diverges: runs forever (this must be bounded in practice).

**Theorem (Critical Pair Lemma, Knuth-Bendix 1970 / Huet 1980):** A TRS R (with infinite variable set) is locally confluent iff all its critical pairs are joinable. By Newman's Lemma, if R is also terminating, then locally confluent ⟺ confluent.

**Theorem (Undecidability, McKenzie 1971):** Whether `E |= E'` is undecidable in general (for unrestricted magma laws). For the fixed set of 4,694 laws of order ≤ 4, the ETP has resolved all cases.

**Theorem (Austin 1979):** `|=_fin` (implication over all finite magmas) is strictly weaker than `|=`. There exist laws E, E' such that every finite magma satisfying E also satisfies E', but some infinite magma does not.

**Theorem (Z3 Completeness for Finite Domains):** For any fixed domain size n, Z3 can decide in finite time whether a satisfying assignment to integer variables exists (DPLL(T) framework). Hence, for each fixed n, Z3 is a complete procedure for finding n-element magma counterexamples.

**Key Statistics (Ground Truth):**
- 4,694 laws × 4,694 laws = 22,028,942 pairs (diagonal excluded)
- Positive implications: 8,178,279 (37.1%)
- Non-implications: 13,855,357 (62.9%)
- CNN baseline: 99.7% accuracy on full matrix

---

## Proof Techniques in the Literature

### Technique 1: BFS Term Rewriting (predictor3, predictor2, predictor1)

- **Method**: Breadth-first search expanding terms reachable from law2's LHS and RHS under law1's rewrite rules. If sets intersect, implication proven.
- **Strength**: Sound and fast for short proofs.
- **Weakness**: Incomplete (bounded search may miss long proofs); does not use the full congruence structure of law1.
- **In predictor3**: `bfs_expand` with limit 550, `MAX_TERM_DEPTH = 15`.

### Technique 2: Knuth-Bendix Completion (proposed replacement for BFS)

- **Method**: Apply KB completion to law1 (as a single equation, symmetric). If it produces a convergent TRS R, check if `NF_R(LHS of law2) = NF_R(RHS of law2)`.
- **Strength**: Complete for the word problem when it terminates. Fundamentally more powerful than BFS — it computes the full equational closure.
- **Weakness**: May not terminate (must use time/step limit). The convergent TRS may be large (many rules).
- **Key tools**: KBCV, MKBTT (not in Python). Must implement KB completion in Python.
- **Implementation**: See `code/README.md` for design notes.
- **Expected gain**: Correctly proves some implications that BFS misses (long rewrite chains, indirect consequences).

### Technique 3: Exhaustive Finite Magma Enumeration (predictor3)

- **Method**: Enumerate many structured finite magmas (all 3^9 = 19,683 size-3 magmas, S3, Q8, etc.) and check if any satisfies law1 but not law2.
- **Strength**: High coverage; size-3 exhaustive enumeration catches most common counterexamples.
- **Weakness**: Hill-climbing for size 4–5 magmas is heuristic; may miss counterexamples.

### Technique 4: Z3 SMT Model Finding (proposed replacement for hill-climbing)

- **Method**: Encode "find a size-n magma satisfying law1 but not law2" as an SMT problem. Z3 either finds a counterexample or proves none exists (for that domain size n).
- **Strength**: **Complete** for each fixed n — no false negatives for counterexamples of that size. Sound by construction (any returned table is a verified counterexample).
- **Weakness**: Slower than heuristic search for larger n (constraint size grows as n^(n²+|vars|)).
- **Performance**: Verified working for n=3, n=4 in under 1 second for 2-variable laws.
- **Encoding**: Table T[i][j] as integer variables in [0,n); law evaluation as If-then-else chain; universal quantification over all variable assignments (explicit); existential violation as `Or([...])`.

### Technique 5: Linear Polynomial Counterexample Search (predictor3, retain)

- **Method**: Evaluate law1 and law2 in commutative polynomial rings Z/pZ. If law1 holds but law2 fails in any ring evaluation, non-implication is proven.
- **Strength**: Very fast algebraic check covering a broad class of counterexamples.
- **Retain**: Yes — this is an efficient complement to Z3 (different class of models).

### Technique 6: Random Polynomial Evaluation over Large Primes (predictor3, retain)

- **Method**: Evaluate laws under random multilinear maps over large primes (640 evaluations). If law1 holds but law2 fails, non-implication proven.
- **Strength**: Probabilistically powerful; provides a soft implication signal.
- **Retain**: Yes.

### Technique 7: Structural Feature Heuristics (predictor3, retain)

- **Method**: When no counterexample found and implication not proven, use structural features (variable counts, subterm similarity, law type, canonical signature similarity) to estimate implication probability.
- **Retain**: Yes, as the fallback probability estimator.

---

## Relationship Between KB Completion and BFS Rewriting

BFS rewriting in predictor3 is essentially a **bounded approximation** to KB completion:

| Aspect | BFS (predictor3) | KB Completion (proposed) |
|--------|-----------------|--------------------------|
| Completeness | Incomplete (bounded) | Complete when it terminates |
| Method | Expand law2's LHS/RHS reachable set | Build convergent TRS from law1 |
| Proof | Implicit (intersection found) | Explicit (normal forms equal) |
| Termination | Always (bounded by limit) | May diverge |
| Complexity | O(limit × rewrite_fanout) | Potentially exponential |
| Python impl | Available in predictor3 | Must implement from scratch |

**Key improvement**: KB completion can prove implications that require arbitrarily long rewrite chains from law2's LHS to law2's RHS, whereas BFS is bounded. For example, if law1 = `x*(y*z) = (x*y)*z` (associativity), KB completion of E = {associativity} produces R = {left or right association rule}, enabling normal form comparison. BFS may miss implications requiring > 550 steps.

---

## Relationship Between Z3 and Hill-Climbing

| Aspect | Hill-climbing (predictor3) | Z3 Model Finding (proposed) |
|--------|--------------------------|------------------------------|
| Completeness | Heuristic (may miss) | Complete for fixed domain size n |
| Method | Stochastic gradient descent on violations | DPLL(T) constraint solving |
| Soundness | High (verified tables) | Exact (formal guarantee) |
| Speed | Fast per restart | Moderate (depends on encoding) |
| Size range | n = 3, 4, 5 | n = 2, 3, 4, 5, 6 (tested) |
| False negatives | Possible | None for given n |

**Key improvement**: Z3 provides **completeness guarantees** for fixed n. A failed Z3 query means no counterexample of size n exists, giving stronger evidence for implication. Hill-climbing may terminate without finding a counterexample that exists.

---

## Implementation Plan for KB Completion

Based on Baader & Nipkow (1999) and Knuth & Bendix (1970):

### 1. Term Ordering (LPO for magma terms)
For magma terms over a single binary operator `*`, a simple effective ordering:
- Variables are ordered by name: `x > y > z > ...` (alphabetically decreasing)
- `s * t > u` if `s ≥ u` or `t ≥ u` (the subterm property)
- `s * t > u * v` if (s,t) >`_lex` (u,v) after considering all cases

For single-equation systems (single law), the only equations to orient are the law itself and critical pairs arising from overlapping rules. LPO can be used to orient rules; if LPO cannot orient an equation in either direction, KB fails for that ordering.

### 2. Unification for Critical Pair Computation
Standard first-order unification (Robinson's algorithm) to find overlaps between rule LHSs.

### 3. KB Inference Rules (simplified for single-equation input):
```
E = {law1}  (symmetric: both law1 and its reverse)
Loop:
  1. Orient all equations in E using LPO → add to R
  2. For all pairs of rules in R, compute critical pairs
  3. Reduce each critical pair by R (rewrite to normal form)
  4. If normal forms differ: add as new equation to E
  5. If normal forms equal: discard (this pair is joinable)
  6. Repeat until E is empty (success) or time/step limit (inconclusive)
```

### 4. Normal Form Computation
Given convergent TRS R, reduce a term by applying rules in R until no rule applies.

### 5. Bound Strategy
Use step limit (e.g., 200 KB steps) and term depth limit (e.g., depth ≤ 20) to prevent divergence.

---

## Gaps and Opportunities

**Gap 1 — KB completion for single-equation equational systems:**
Most KB completion implementations and papers focus on multi-equation systems (groups, rings, etc.). Single-equation systems (one magma law) often terminate quickly or produce small TRSs, making them tractable.

**Gap 2 — Z3 encoding efficiency:**
The If-then-else chain encoding has quadratic constraint size in n (n² table variables × n^|vars| universal quantification). For n=5, 4-variable laws have 5^4 = 625 assignments × 25 table constraints — still tractable for Z3.

**Gap 3 — Integration threshold:**
When to invoke KB vs. fall back to BFS? Suggested strategy: try KB with a 1-second timeout; if it terminates and proves implication, return high confidence; if timeout, fall back to BFS behavior.

**Gap 4 — Z3 vs. exhaustive size-3 enumeration:**
For size 3, all 19,683 tables can be enumerated in ~0.1s in Python. Z3 is slower for size 3 than exhaustive enumeration. Strategy: keep exhaustive enumeration for n=2 and n=3; use Z3 for n=4 and n=5 (where exhaustive is infeasible).

---

## Recommendations for Proof Strategy

1. **For positive implication (law1 |= law2):**
   - First: try direct specialization (law2 is a substitution instance of law1)
   - Second: run KB completion on law1 with 1-second timeout
   - If KB succeeds and `NF_R(LHS2) = NF_R(RHS2)`: return 0.9999
   - If KB times out: fall back to BFS (predictor3's `bfs_expand`)

2. **For negative implication (law1 ⊭ law2):**
   - First: linear polynomial check (fast algebraic counterexample)
   - Second: random polynomial evaluation over large primes
   - Third: exhaustive enumeration for n=2, n=3
   - Fourth: Z3 model finding for n=4 and n=5 (complete for these sizes)
   - If any check finds a counterexample: return 0.0001

3. **Fallback probability estimation:**
   - If neither proven nor disproven: use structural features + coverage ratio
   - Same framework as predictor3 (adjusted adj factors based on results)

4. **Expected accuracy improvement over predictor3:**
   - KB completion catches long-chain implications that BFS misses
   - Z3 (complete for n=4, n=5) catches counterexamples that hill-climbing misses
   - Together: should improve log-loss more than accuracy (by increasing confidence)
