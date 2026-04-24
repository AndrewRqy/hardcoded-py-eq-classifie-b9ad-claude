"""Quick test of predictor4 vs predictor3 on 50 cases."""
import sys, math, random, time, json
sys.path.insert(0, '/workspaces/hardcoded-py-eq-classifie-b9ad-claude/src')
sys.path.insert(0, '/workspaces/hardcoded-py-eq-classifie-b9ad-claude/code/predictor3/src')
sys.path.insert(0, '/workspaces/hardcoded-py-eq-classifie-b9ad-claude/code/equational_theories/scripts/predictor')

import predictor4, predictor3

EQUATIONS_FILE = '/workspaces/hardcoded-py-eq-classifie-b9ad-claude/code/equational_theories/scripts/predictor/equations.txt'
IMPLICATIONS_FILE = '/workspaces/hardcoded-py-eq-classifie-b9ad-claude/code/equational_theories/scripts/predictor/raw_implications.csv'

with open(EQUATIONS_FILE) as f:
    equations = [line.strip() for line in f if line.strip()]

print("Loading matrix...")
import pandas as pd
df = pd.read_csv(IMPLICATIONS_FILE, header=None)
matrix = df.values
n_laws = len(equations)

# Sample 50 cases (25 impl, 25 non-impl)
random.seed(42)
all_idx = [(i, j) for i in range(n_laws) for j in range(n_laws) if i != j]
random.shuffle(all_idx)

impl_triples, non_impl_triples = [], []
for i, j in all_idx:
    val = matrix[i, j]
    is_impl = bool(val > 0)
    t = (equations[i], equations[j], is_impl)
    if is_impl and len(impl_triples) < 25:
        impl_triples.append(t)
    elif not is_impl and len(non_impl_triples) < 25:
        non_impl_triples.append(t)
    if len(impl_triples) >= 25 and len(non_impl_triples) >= 25:
        break

triples = impl_triples + non_impl_triples
random.shuffle(triples)
print(f"Testing on {len(triples)} cases ({len(impl_triples)} impl, {len(non_impl_triples)} non-impl)")

def log_loss(p, is_impl):
    eps = 1e-9
    p = max(eps, min(1-eps, p))
    return math.log(p) if is_impl else math.log(1-p)

def run_eval(predictor_fn, name):
    correct, total_ll, t_total = 0, 0, 0
    fp, fn = 0, 0
    for law1, law2, is_impl in triples:
        t0 = time.time()
        p = predictor_fn(law1, law2)
        elapsed = time.time() - t0
        t_total += elapsed
        ll = log_loss(p, is_impl)
        c = (p > 0.5) == is_impl
        correct += c
        total_ll += ll
        if not is_impl and p > 0.5: fp += 1
        if is_impl and p < 0.5: fn += 1
    print(f"[{name}] Acc: {correct}/{len(triples)} ({100*correct/len(triples):.1f}%), AvgLL: {total_ll/len(triples):.4f}, FP: {fp}, FN: {fn}, Time: {t_total:.1f}s")
    return correct, total_ll

print("\nRunning predictor3...")
c3, ll3 = run_eval(predictor3.predict_implication_probability, "predictor3")
print("\nRunning predictor4...")
c4, ll4 = run_eval(predictor4.predict_implication_probability, "predictor4")

print(f"\nImprovement: acc {c4-c3:+d}, log-loss {ll4-ll3:+.4f}")
