# Computational Tools

## Tool 1: predictor3 (Previous Classifier)

- **URL**: https://github.com/AndrewRqy/hardcoded-eq-implication-f0c0-claude
- **Location**: `code/predictor3/`
- **Purpose**: The predecessor classifier using BFS term rewriting (positive implication), hill-climbing finite magma search (negative implication), and random polynomial evaluation. Achieved 100% accuracy on a 1000-sample evaluation with log-loss -0.0016.
- **Key scripts**:
  - `src/predictor3.py` — Main classifier (~660 lines)
  - `src/evaluate.py`, `src/evaluate2.py` — Evaluation harnesses
  - `src/diagnose.py`, `src/diagnose2.py` — Per-case diagnostic tools
- **Components to replace**:
  - BFS term rewriting (`bfs_expand`) → Knuth-Bendix completion
  - Hill-climbing magma search (`generate_magmas` hill-climb section) → Z3 SMT model finding
- **Components to retain**: Linear polynomial counterexample search, structured algebraic families (S3, Q8, etc.), structural feature-based probability adjustment, random polynomial evaluation over large primes

## Tool 2: equational_theories (Teorth's ETP Repository)

- **URL**: https://github.com/teorth/equational_theories
- **Location**: `code/equational_theories/`
- **Purpose**: The main Equational Theories Project repository. Contains:
  - Ground truth data: `scripts/predictor/raw_implications.csv` (4693×4693 matrix, ±3/±4 values)
  - Equation list: `scripts/predictor/equations.txt` (4,694 laws)
  - Reference predictors: `scripts/predictor/predictor1.py`, `scripts/predictor/predictor2.py`
  - Test harness: `scripts/predictor/test.py`, `scripts/predictor/short_test.py`
  - Evaluation triples: `scripts/predictor/generated_triples.py`, `scripts/predictor/hard_triples.py`
- **Data format**: `raw_implications.csv` is a dense integer matrix. Value `+3` or `+4` means proven implication; `-3` or `-4` means proven non-implication. The sign encodes the proof method.
- **Key usage**: Run `test.py` with a custom predictor to evaluate on random or hard triples.

## Tool 3: Z3 SMT Solver (Python API)

- **Package**: `z3-solver==4.16.0`
- **Installed**: Yes (via `uv pip install z3-solver`)
- **Purpose**: Used for **negative implication** (counterexample finding). Z3 encodes the constraint "find a finite magma of size n satisfying law1 but not law2" as an SMT problem:
  - Variables: `T[i][j]` for each table cell (IntSort, domain [0,n))
  - Law evaluation via If-then-else chains for symbolic table lookup
  - Universal quantification via explicit enumeration of all variable assignments
  - Existential violation via `Or([...])` over all possible assignments
- **Performance**: Verified working for n=3 and n=4 in under 1 second for 2-variable laws.
- **Key limitation**: For n=6 with 4-variable laws, the constraint size grows as n^4 = 1296 variable assignments × n^(n^2) table entries.

## Tool 4: SymPy (Symbolic Mathematics)

- **Package**: `sympy==1.14.0`
- **Installed**: Yes (via `uv pip install sympy`)
- **Purpose**: Available for symbolic computation, though no built-in KB completion. Useful for polynomial/Groebner basis computation as a secondary counterexample method.

## Notes on Knuth-Bendix Completion

No Python package implementing KB completion is available on PyPI. The implementation must be written from scratch based on:
1. Baader & Nipkow (1999), Chapter 7: "Completion"
2. Knuth & Bendix (1970): Original algorithm
3. Sternagel et al. (2012): Recording completion variant

Key implementation requirements:
- **Term representation**: S-expression trees (matching predictor3's tuple format)
- **Reduction order**: Lexicographic path order (LPO) or Knuth-Bendix order (KBO) for orienting equations into rules
- **Critical pair computation**: For each pair of rules in R, compute overlaps and check joinability
- **Termination**: KB completion may not terminate; must use a step/time limit
- **For magma laws**: Terms are binary trees; the LPO based on variable ordering works well
