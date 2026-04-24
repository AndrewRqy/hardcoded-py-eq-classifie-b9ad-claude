"""
Benchmark predictor4 vs predictor3 on random samples from the ground truth matrix.
"""
import sys
import os
import math
import random
import time
import json

sys.path.insert(0, '/workspaces/hardcoded-py-eq-classifie-b9ad-claude/src')
sys.path.insert(0, '/workspaces/hardcoded-py-eq-classifie-b9ad-claude/code/predictor3/src')
sys.path.insert(0, '/workspaces/hardcoded-py-eq-classifie-b9ad-claude/code/equational_theories/scripts/predictor')

import predictor4
import predictor3

EQUATIONS_FILE = '/workspaces/hardcoded-py-eq-classifie-b9ad-claude/code/equational_theories/scripts/predictor/equations.txt'
IMPLICATIONS_FILE = '/workspaces/hardcoded-py-eq-classifie-b9ad-claude/code/equational_theories/scripts/predictor/raw_implications.csv'

def load_data():
    with open(EQUATIONS_FILE) as f:
        equations = [line.strip() for line in f if line.strip()]

    print(f"Loading {IMPLICATIONS_FILE}...")
    import pandas as pd
    df = pd.read_csv(IMPLICATIONS_FILE, header=None)
    matrix = df.values
    print(f"Loaded {len(equations)} equations, matrix shape {matrix.shape}")
    return equations, matrix


def log_loss(p, is_impl):
    eps = 1e-9
    p = max(eps, min(1 - eps, p))
    return math.log(p) if is_impl else math.log(1 - p)


def evaluate_all(triples, predictor_fn, name, verbose=False):
    results = []
    t0 = time.time()
    for i, (law1, law2, is_impl) in enumerate(triples):
        t_start = time.time()
        try:
            p = predictor_fn(law1, law2)
        except Exception as e:
            p = 0.5
        elapsed = time.time() - t_start
        ll = log_loss(p, is_impl)
        correct = (p > 0.5) == is_impl
        results.append({'p': p, 'is_impl': is_impl, 'log_loss': ll, 'correct': correct, 'time': elapsed})
        if verbose and (i % 20 == 0):
            print(f"  [{name}] {i}/{len(triples)}: p={p:.4f} actual={is_impl} ll={ll:.4f} t={elapsed:.2f}s")
    total_time = time.time() - t0
    accuracy = sum(r['correct'] for r in results) / len(results)
    avg_ll = sum(r['log_loss'] for r in results) / len(results)
    fp = sum(1 for r in results if not r['is_impl'] and r['p'] > 0.5)
    fn = sum(1 for r in results if r['is_impl'] and r['p'] < 0.5)
    print(f"\n[{name}] Accuracy: {accuracy:.4f} ({sum(r['correct'] for r in results)}/{len(results)})")
    print(f"[{name}] Avg Log-Loss: {avg_ll:.4f}")
    print(f"[{name}] False Positives: {fp}, False Negatives: {fn}")
    print(f"[{name}] Total time: {total_time:.1f}s, Avg: {total_time/len(results):.2f}s/pair")
    return results


def main():
    random.seed(42)
    equations, matrix = load_data()
    n_laws = len(equations)

    # Sample 200 random pairs (stratified: ~100 implications, ~100 non-implications)
    N = 200
    triples = []
    impl_triples = []
    non_impl_triples = []

    all_indices = [(i, j) for i in range(n_laws) for j in range(n_laws) if i != j]
    random.shuffle(all_indices)

    for i, j in all_indices:
        val = matrix[i, j]
        is_impl = bool(val > 0)
        triple = (equations[i], equations[j], is_impl)
        if is_impl and len(impl_triples) < N // 2:
            impl_triples.append(triple)
        elif not is_impl and len(non_impl_triples) < N // 2:
            non_impl_triples.append(triple)
        if len(impl_triples) >= N // 2 and len(non_impl_triples) >= N // 2:
            break

    triples = impl_triples + non_impl_triples
    random.shuffle(triples)
    print(f"\nSelected {len(triples)} test cases ({len(impl_triples)} implications, {len(non_impl_triples)} non-implications)")

    # Save test cases
    with open('/workspaces/hardcoded-py-eq-classifie-b9ad-claude/results/test_cases.json', 'w') as f:
        json.dump([{'law1': t[0], 'law2': t[1], 'is_impl': t[2]} for t in triples], f, indent=2)

    print("\n--- Benchmarking predictor3 ---")
    res3 = evaluate_all(triples, predictor3.predict_implication_probability, 'predictor3', verbose=True)

    print("\n--- Benchmarking predictor4 ---")
    res4 = evaluate_all(triples, predictor4.predict_implication_probability, 'predictor4', verbose=True)

    # Detailed comparison
    print("\n=== COMPARISON ===")
    improvements = sum(1 for r3, r4 in zip(res3, res4)
                       if not r3['correct'] and r4['correct'])
    regressions = sum(1 for r3, r4 in zip(res3, res4)
                      if r3['correct'] and not r4['correct'])
    ll_improvement = sum(r4['log_loss'] - r3['log_loss'] for r3, r4 in zip(res3, res4))

    print(f"Cases improved (predictor3 wrong, predictor4 correct): {improvements}")
    print(f"Cases regressed (predictor3 correct, predictor4 wrong): {regressions}")
    print(f"Net log-loss improvement: {ll_improvement:.4f}")

    # Save results
    summary = {
        'predictor3': {
            'accuracy': sum(r['correct'] for r in res3) / len(res3),
            'avg_log_loss': sum(r['log_loss'] for r in res3) / len(res3),
            'false_positives': sum(1 for r in res3 if not r['is_impl'] and r['p'] > 0.5),
            'false_negatives': sum(1 for r in res3 if r['is_impl'] and r['p'] < 0.5),
        },
        'predictor4': {
            'accuracy': sum(r['correct'] for r in res4) / len(res4),
            'avg_log_loss': sum(r['log_loss'] for r in res4) / len(res4),
            'false_positives': sum(1 for r in res4 if not r['is_impl'] and r['p'] > 0.5),
            'false_negatives': sum(1 for r in res4 if r['is_impl'] and r['p'] < 0.5),
        },
        'improvements': improvements,
        'regressions': regressions,
        'net_ll_improvement': ll_improvement,
        'n_test_cases': len(triples),
    }
    with open('/workspaces/hardcoded-py-eq-classifie-b9ad-claude/results/benchmark_results.json', 'w') as f:
        json.dump(summary, f, indent=2)
    print("\nResults saved to results/benchmark_results.json")

    # KB-specific analysis
    print("\n=== KB COMPLETION ANALYSIS ===")
    from predictor4 import kb_prove_implication, parse
    kb_proved = 0
    kb_correct_proofs = 0
    for law1, law2, is_impl in triples:
        t1 = tuple(parse(x) for x in law1.split('='))
        t2 = tuple(parse(x) for x in law2.split('='))
        kb_res = kb_prove_implication(t1, t2)
        if kb_res is True:
            kb_proved += 1
            if is_impl:
                kb_correct_proofs += 1
            else:
                print(f"  KB FALSE POSITIVE: {law1} |= {law2} (actual: NOT implication)")
    print(f"KB proved {kb_proved} implications, {kb_correct_proofs} correct (soundness: {kb_correct_proofs/max(1,kb_proved):.4f})")


if __name__ == '__main__':
    main()
