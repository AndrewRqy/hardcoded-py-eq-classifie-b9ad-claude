# Downloaded Papers

## Paper 1: Recording Completion for Finding and Certifying Proofs in Equational Logic

- **Authors**: Thomas Sternagel, René Thiemann, Harald Zankl, Christian Sternagel
- **Year**: 2012
- **arXiv**: 1208.1597v1
- **File**: [recording_completion_equational_logic_Sternagel2012.pdf](recording_completion_equational_logic_Sternagel2012.pdf)
- **Why relevant**: Core reference for Knuth-Bendix (KB) completion applied to equational implication. Explains how a successful KB run produces a convergent TRS R equivalent to the equation set E, enabling the decision s ↔*_E t iff R-normal forms of s and t coincide. Also introduces "recording completion" that tracks derivation history for proof certification. Directly relevant to the hypothesis of replacing BFS term rewriting with KB completion for positive implication detection.

## Paper 2: Equational Theories and Validity for Logically Constrained Term Rewriting (Full Version)

- **Authors**: (see paper)
- **Year**: 2024
- **arXiv**: 2405.01174v3
- **File**: [equational_theories_validity_constrained_rewriting_2024.pdf](equational_theories_validity_constrained_rewriting_2024.pdf)
- **Why relevant**: Extends equational theory and term rewriting to logically constrained rewriting systems, relevant to understanding the boundary between equational validity and SMT-based checking. Background on equational implication decidability in the presence of constraints.

## Key References (not downloaded — classics/textbooks)

### Knuth & Bendix (1970)
- **Authors**: Donald E. Knuth, Peter B. Bendix
- **Title**: "Simple Word Problems in Universal Algebras"
- **Source**: In J. Leech (ed.), *Computational Problems in Abstract Algebra*, pp. 263–297, Pergamon Press
- **Why relevant**: Original paper introducing the Knuth-Bendix completion algorithm for deciding the word problem in equational theories. The foundational reference for the KB completion component of the proposed classifier.

### Baader & Nipkow (1999) — "Term Rewriting and All That"
- **Authors**: Franz Baader, Tobias Nipkow
- **Publisher**: Cambridge University Press
- **Why relevant**: Standard textbook on term rewriting systems. Covers KB completion, termination, confluence, and critical pairs — all prerequisite concepts for implementing KB completion for magma equations.

### Birkhoff (1935)
- **Authors**: Garrett Birkhoff
- **Title**: "On the structure of abstract algebras"
- **Source**: *Proc. Cambridge Phil. Soc.*, 31:433–454
- **Why relevant**: Proves Birkhoff's completeness theorem: E |= E' iff LHS of E' is reachable from RHS via equational rewriting under E. This is the theoretical basis for all BFS/KB-based positive implication provers.

### de Moura & Bjørner (2008) — Z3
- **Authors**: Leonardo de Moura, Nikolaj Bjørner
- **Title**: "Z3: An Efficient SMT Solver"
- **Source**: TACAS 2008, LNCS 4963, pp. 337–340
- **Why relevant**: Introduces Z3, the SMT solver used for negative implication detection (finding finite magma counterexamples). Z3 encodes the constraint "find a magma satisfying law1 but not law2" for bounded domain sizes.
