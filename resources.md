# Resources Catalog

## Summary

This document catalogs all resources gathered for the mathematics research project: **Advanced Hard-Coded Python Classifier for Equational Implication over Magmas** — specifically, replacing BFS term rewriting with Knuth-Bendix completion and replacing hill-climbing with Z3 SMT model finding.

---

## Papers

Total papers downloaded: 2 (+ 4 key references documented but not downloaded)

| Title | Authors | Year | File | Key Results |
|-------|---------|------|------|-------------|
| Recording Completion for Finding and Certifying Proofs in Equational Logic | Sternagel, Thiemann, Zankl, Sternagel | 2012 | papers/recording_completion_equational_logic_Sternagel2012.pdf | KB completion inference rules; three-phase structure for proof construction; soundness theorem |
| Equational Theories and Validity for Logically Constrained Term Rewriting | (see paper) | 2024 | papers/equational_theories_validity_constrained_rewriting_2024.pdf | Equational validity in constrained TRS; SMT-equational interface |

Key undowloaded references:
| Title | Authors | Year | Source | Key Results |
|-------|---------|------|--------|-------------|
| Simple Word Problems in Universal Algebras | Knuth, Bendix | 1970 | Pergamon Press (book chapter) | Original KB completion algorithm; completion as word problem decision procedure |
| Term Rewriting and All That | Baader, Nipkow | 1999 | Cambridge University Press | Standard reference for TRS theory, KB completion, LPO, confluence |
| Z3: An Efficient SMT Solver | de Moura, Bjørner | 2008 | TACAS 2008 | Z3 DPLL(T) framework; quantifier-free integer arithmetic |
| The Equational Theories Project | Tao et al. | 2025 | arXiv:2512.07087v2 | Complete ground truth for 4,694 magma laws; CNN baseline 99.7% |

See `papers/README.md` for detailed descriptions.

---

## Prior Results Catalog

Key theorems and lemmas available for proof construction:

| Result | Source | Statement Summary | Used For |
|--------|--------|-------------------|----------|
| Birkhoff Completeness | Birkhoff (1935) | E \|= E' iff E' derivable from E by equational rewriting | Justifies BFS and KB as positive implication provers |
| KB Soundness/Completeness | Knuth-Bendix (1970) | If KB(E) = R (convergent), then s ↔*_E t iff NF_R(s) = NF_R(t) | Core guarantee for KB-based positive implication |
| Critical Pair Lemma | Huet (1980) | Terminating TRS is confluent iff all critical pairs joinable | Correctness check for KB completion |
| Austin (1979) | Austin | ∃ E, E': E \|=_fin E' but E ⊭ E' | Shows finite model search may miss some non-implications |
| McKenzie Undecidability | McKenzie (1971) | General equational implication undecidable | Explains why KB and Z3 must use bounded search |
| Z3 Completeness (finite domain) | Z3 theory | For fixed n, Z3 decides satisfiability in finite time | Justifies Z3 as complete counterexample finder for fixed n |
| Recording Completion Soundness | Sternagel et al. (2012) | Every successful recording completion run produces correct convergent TRS | Validates our KB implementation approach |

---

## Computational Tools

| Tool | Purpose | Location | Notes |
|------|---------|----------|-------|
| z3-solver 4.16.0 | SMT-based finite magma counterexample finding | pip package | Installed; tested for n=3,4 |
| sympy 1.14.0 | Symbolic computation (backup polynomial methods) | pip package | Installed |
| predictor3 | Previous classifier (BFS + hill-climbing baseline) | code/predictor3/ | Reference implementation to improve upon |
| equational_theories | Ground truth data + evaluation harness | code/equational_theories/ | Contains raw_implications.csv (22M ground truth) |

---

## Resource Gathering Notes

### Search Strategy

1. **arXiv search**: Queries for "Knuth-Bendix completion equational theories", "SMT Z3 model finding finite algebra", "equational implication magma counterexample", "recording completion equational logic". Key hit: Sternagel et al. (1208.1597).

2. **GitHub cloning**: Cloned `predictor3` (previous classifier) and `equational_theories` (ETP repository with ground truth).

3. **Paper-finder service**: Unavailable (service not running at localhost:8000). Fell back to arXiv and Semantic Scholar (rate-limited).

4. **Manual identification**: The equational theories project paper (arXiv:2512.07087v2), Baader & Nipkow textbook, Knuth-Bendix original paper, and de Moura & Bjørner Z3 paper identified as key references from prior literature review in predictor3.

### Selection Criteria

- **Recording Completion paper**: Directly relevant to the KB completion component; provides the inference rules, soundness theorem, and implementation guidance.
- **Constrained TRS paper**: Background on SMT-equational interface; validates our approach.
- **predictor3**: Essential baseline; its BFS and hill-climbing components are the explicit targets for replacement.
- **equational_theories**: Contains ground truth (raw_implications.csv) and evaluation harness (test.py).

### Key Implementation Findings

1. **No Python KB completion library exists** on PyPI. Implementation must be written from scratch using Baader & Nipkow as the reference.

2. **Z3 works for magma model finding**: Tested with If-then-else chain encoding for symbolic table lookup. Works correctly for n=3, n=4.

3. **KB completion for single-equation equational systems** (one magma law) is simpler than the general case: only one symmetric rule pair to start from, critical pairs are limited, and many laws produce small convergent TRSs quickly.

4. **Evaluation harness**: `code/equational_theories/scripts/predictor/test.py` provides the evaluation framework. Predictor must expose `predict_implication_probability(law1: str, law2: str) -> float`.

---

## Recommendations for Proof Construction

1. **Proof strategy**: Implement KB completion as a new positive implication prover, replacing the BFS `bfs_expand` function in predictor3. Keep all other predictor3 components unchanged initially; measure improvement.

2. **Key prerequisites to implement**:
   - Term unification (Robinson's algorithm) for critical pair computation
   - LPO term ordering for rule orientation
   - KB completion loop with step/time limit
   - Normal form computation under a convergent TRS

3. **Z3 integration**: Replace hill-climbing (`generate_magmas` hill-climb section) with Z3 model finding for n=4 and n=5. Keep exhaustive enumeration for n=2, n=3.

4. **Potential difficulties**:
   - KB completion may time out for laws that require many critical pairs to resolve (e.g., complex 4-variable laws)
   - Z3 encoding may be slow for n=5 with 3–4-variable laws (5^4 = 625 variable assignments)
   - The interaction between KB and the fallback probability estimator needs careful calibration

5. **Risk mitigation**: The fallback to BFS (when KB times out) and to hill-climbing (when Z3 times out) ensures we don't regress below predictor3's performance. The improvements from KB and Z3 are strictly additive.
