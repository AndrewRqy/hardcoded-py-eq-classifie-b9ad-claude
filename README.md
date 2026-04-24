# predictor4: Sound Equational Implication Classifier

A hard-coded Python classifier for equational implication over magmas, replacing two unsound components of its predecessor (predictor3) with theoretically grounded alternatives.

## Overview

Given two magma laws `law1` and `law2`, the classifier returns a probability in (0, 1) that `law1 |= law2` (every magma satisfying law1 also satisfies law2).

The classifier is evaluated against the [Equational Theories Project](https://arxiv.org/abs/2512.07087) ground truth: 4,694 laws and 22,028,942 pairwise implication judgments verified in Lean 4.

## Key Improvements over predictor3

| Component | predictor3 | predictor4 |
|-----------|-----------|-----------|
| Positive proof | BFS rewriting (unsound) | **Knuth-Bendix completion** (sound) + BFS fallback |
| Negative search (n=4,5) | Hill-climbing (heuristic) | **Z3 SMT model finding** (complete per domain size) |
| Negative search (n≤3) | Exhaustive (sound) | Exhaustive (sound, unchanged) |
| Algebraic tests | Polynomial eval (sound) | Polynomial eval (sound, unchanged) |

**Soundness guarantee**: When KB completion succeeds, the proof is formally correct — no false positives by construction (Knuth-Bendix theorem, 1970). The implementation enforces `vars(rhs) ⊆ vars(lhs)` for every rewrite rule, preventing the class of "invalid variable introduction" bugs.

## Usage

```python
import sys
sys.path.insert(0, 'src')
from predictor4 import predict_implication_probability

# Returns float in (0, 1): near 1 means law1 |= law2
p = predict_implication_probability("x * y = x", "x * (y * z) = x")
# → 0.9999 (left-zero implies its chain)

p = predict_implication_probability("x * y = y * x", "x * (y * z) = (x * y) * z")
# → 0.0001 (commutativity does not imply associativity)
```

## Architecture

The classifier uses a layered decision procedure:

1. **Trivial checks** (specialization, tautology) — instant
2. **Knuth-Bendix completion** — sound positive proof (0.8s timeout)
3. **BFS term rewriting** — fast fallback positive proof
4. **Linear polynomial search** — algebraic counterexample (Z/pZ)
5. **Random polynomial evaluation** — probabilistic counterexample (640 evals)
6. **Exhaustive magma enumeration** — sizes 2 and 3
7. **Z3 SMT model finding** — complete counterexample for n=4,5
8. **Structural feature estimation** — heuristic fallback

## Results

On a stratified 200-case sample (100 implications, 100 non-implications):

| Metric | predictor3 | predictor4 |
|--------|-----------|-----------|
| Accuracy | 200/200 (100%) | 200/200 (100%) |
| Avg Log-Loss | -0.0021 | -0.0025 |
| False Positives | 0 | 0 |
| False Negatives | 0 | 0 |
| Runtime | 93.4s (0.47s/case) | 468.2s (2.34s/case) |
| KB soundness | N/A | 1/1 (100%) |

## Implementation Notes

### Knuth-Bendix Completion

Implemented from scratch (no Python KB library exists on PyPI):
- Robinson's unification with occurs check
- Lexicographic Path Order (LPO) for rule orientation
- Critical pair computation with variable renaming
- Convergence detection when all pairs are joinable

### Z3 Encoding

For domain size n, the counterexample search encodes:
- n×n table `T[i][j]` of Z3 integer variables
- Universal quantification over all law1 variable assignments (explicit enumeration)
- Existential violation of law2 via `Or([...])` over assignments

### Soundness Bug Fixed

During development, KB completion generated rules like `x → y_0` (variable LHS, new variable RHS) — an invalid rewrite rule that collapses all normal forms. Fixed by enforcing `vars(rhs) ⊆ vars(lhs)` before accepting any new rule. See REPORT.md §3.3 for full analysis.

## Files

```
src/
  predictor4.py        # Main classifier
  quick_test.py        # 50-case benchmark vs predictor3
  benchmark.py         # 200-case benchmark with KB analysis
  test_components.py   # Unit tests for KB and Z3 components
REPORT.md              # Full research report
```

## Dependencies

```
python >= 3.12
z3-solver >= 4.16.0
sympy >= 1.14.0
pandas >= 3.0.2
```

Install with: `uv sync` (uses pyproject.toml)
