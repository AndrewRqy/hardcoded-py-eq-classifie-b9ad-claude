# Planning: Advanced Hard-Coded Python Classifier for Equational Implication

## Motivation & Novelty Assessment

### Why This Research Matters
Equational implication classification over magmas is a foundational problem in universal algebra and automated theorem proving. The Equational Theories Project verified 22M pairwise implications with formal Lean proofs; a fast, sound Python classifier enables rapid hypothesis testing and serves as a practical tool for algebraic research. Sound classification is critical: a false positive (claiming law1 |= law2 when it does not) corrupts downstream algebraic reasoning.

### Gap in Existing Work
predictor3's BFS engine can spuriously "prove" false implications when reachable-term sets collide through deep rewrite chains, returning 0.9999 incorrectly for non-implications. Its hill-climbing (sizes 3-5) is heuristic and misses counterexamples requiring larger magmas. Both represent unsound or incomplete components that compromise correctness.

### Our Novel Contribution
Replace BFS with Knuth-Bendix (KB) completion (sound, complete for the word problem when it terminates) and replace hill-climbing with Z3 SMT model finding (complete for each fixed domain size n). These are well-established sound procedures not previously integrated into Python-based equational implication classifiers.

### Experiment Justification
- **KB completion**: Proves positive implications via normal form comparison under a convergent TRS — no false proofs possible.
- **Z3 model finding**: Finds counterexamples or proves none exists for given n — complete for each fixed n.
- **Accuracy benchmark**: Evaluate on 200 random triples from the ground truth matrix to measure improvement over predictor3 baseline.

---

## Research Question
Does replacing BFS term rewriting with Knuth-Bendix completion (positive path) and hill-climbing with Z3 SMT model finding (negative path) increase soundness and classification accuracy for equational implication over magmas?

## Hypothesis Decomposition
1. H1: KB completion proves strictly more positive implications than BFS (KB is complete when it terminates; BFS is bounded).
2. H2: Z3 model finding finds strictly more counterexamples than hill-climbing for fixed sizes (Z3 is complete for each n; hill-climbing is heuristic).
3. H3: The combined predictor4 achieves higher accuracy and lower log-loss than predictor3 on random samples from the full 22M matrix.
4. H4: predictor4 eliminates false positives (spurious implications) in the BFS-collision cases identified in error analysis.

## Proposed Methodology

### Approach
1. Implement KB completion in Python (no external library exists):
   - Term unification (Robinson's algorithm)
   - LPO term ordering for rule orientation
   - KB completion loop with step/time limit
   - Normal form computation under convergent TRS

2. Integrate Z3 SMT model finding:
   - Encode magma table as integer variables in Z3
   - Universal quantification over all variable assignments (explicit)
   - For n = 4, 5, 6 (exhaustive covers n=2, n=3 already)
   - Replace hill-climbing section in generate_magmas()

3. Compose predictor4:
   - Keep all of predictor3's components (parsing, trivial checks, linear polynomial, random polynomial, exhaustive enumeration)
   - Replace BFS with KB completion (with BFS fallback on timeout)
   - Replace hill-climbing with Z3 (with graceful timeout handling)
   - Keep structural feature probability estimation as fallback

### Evaluation Metrics
- **Accuracy**: fraction of 200 random samples correctly classified (threshold 0.5)
- **Log-loss**: sum of log-likelihood values (higher = better)
- **False positive rate**: fraction of non-implications classified with p > 0.5
- **False negative rate**: fraction of true implications classified with p < 0.5

### Success Criteria
- predictor4 accuracy ≥ predictor3 accuracy on the same test set
- predictor4 log-loss ≥ predictor3 log-loss
- Zero false positives from KB (verified by construction)

## Timeline
- Phase 1 (Planning): complete
- Phase 2 (Implementation): ~90 min — KB completion, Z3 integration, predictor4.py
- Phase 3 (Testing): ~30 min — run on 200 random samples, compare with predictor3
- Phase 4 (Analysis): ~20 min — examine error cases, compute metrics
- Phase 5 (Documentation): ~20 min — REPORT.md, README.md

## Potential Challenges
- KB completion may diverge for complex laws → mitigate with step/time limit
- Z3 encoding for 4-variable laws at n=5 may be slow (5^4 = 625 assignments) → time limit
- LPO may fail to orient some equations → detect and skip (KB fails gracefully)
