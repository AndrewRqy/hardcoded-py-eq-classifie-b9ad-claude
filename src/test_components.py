"""Quick sanity tests for KB completion and Z3 model finding."""
import sys
sys.path.insert(0, '/workspaces/hardcoded-py-eq-classifie-b9ad-claude/src')
from predictor4 import (parse, kb_completion, kb_prove_implication, z3_find_counterexample,
                         predict_implication_probability)

def test_kb():
    print("=== KB Completion Tests ===")

    # Test 1: idempotency x*x = x implies commutativity? NO
    # This should NOT be proven
    law1 = (parse('x * x'), parse('x'))  # x*x = x (idempotency)
    law2 = (parse('x * y'), parse('y * x'))  # commutativity
    result = kb_prove_implication(law1, law2)
    print(f"idempotency |= commutativity: {result} (expected: False or None)")

    # Test 2: x = x*y implies x*y = x? Yes (direct)
    law1 = (parse('x'), parse('x * y'))  # left projection x = x*y
    law2 = (parse('x * y'), parse('x'))  # reverse
    result = kb_prove_implication(law1, law2)
    print(f"left_proj_variant |= lp: {result} (expected: True)")

    # Test 3: associativity: x*(y*z)=(x*y)*z - does it imply x*x=x? NO
    law1 = (parse('x * (y * z)'), parse('(x * y) * z'))
    law2 = (parse('x * x'), parse('x'))
    result = kb_prove_implication(law1, law2)
    print(f"associativity |= idempotency: {result} (expected: False or None)")

    # Test 4: x*y = y*x (commutativity) KB completion should terminate
    law1 = (parse('x * y'), parse('y * x'))
    rules, success = kb_completion(law1)
    print(f"KB of commutativity: success={success}, rules={len(rules)}")

    # Test 5: law1 = x*(y*z) = (x*y)*z (assoc). Does it imply x*y*z = x*(y*z)? Yes
    # (they're the same by parenthesization)
    law1 = (parse('x * (y * z)'), parse('(x * y) * z'))
    law2 = (parse('x * (y * z)'), parse('x * (y * z)'))  # trivial
    result = kb_prove_implication(law1, law2)
    print(f"assoc |= trivial: {result} (expected: True)")


def test_z3():
    print("\n=== Z3 Model Finding Tests ===")

    # Test 1: commutativity does not imply associativity
    law1 = (parse('x * y'), parse('y * x'))
    law2 = (parse('x * (y * z)'), parse('(x * y) * z'))
    cex = z3_find_counterexample(law1, law2, n=3, timeout_ms=5000)
    if cex is not None:
        print(f"comm ⊭ assoc: counterexample of size 3 found: {cex[:2]}...")
    else:
        print(f"comm ⊭ assoc: no size-3 counterexample found (unexpected)")

    # Test 2: left projection implies right projection? NO
    law1 = (parse('x * y'), parse('x'))
    law2 = (parse('x * y'), parse('y'))
    cex = z3_find_counterexample(law1, law2, n=2, timeout_ms=5000)
    print(f"lp ⊭ rp: counterexample size 2 = {cex is not None} (expected True)")

    # Test 3: x = x*y and x*y = x (same thing reversed) — should be SAT? No
    # Actually if we encode x=x*y as law1, then x*y=x is the same equation
    law1 = (parse('x'), parse('x * y'))
    law2 = (parse('x * y'), parse('x'))
    cex = z3_find_counterexample(law1, law2, n=3, timeout_ms=5000)
    print(f"x=x*y ⊭ x*y=x: counterexample size 3 = {cex is not None} (expected False — it's the same eq)")


def test_full_predictor():
    print("\n=== Full Predictor Tests ===")
    test_cases = [
        # (law1, law2, expected_implication, description)
        ("x * y = y * x", "x * (y * z) = (x * y) * z", False, "comm ⊭ assoc"),
        ("x * (y * z) = (x * y) * z", "x * y = y * x", False, "assoc ⊭ comm"),
        ("x * y = x", "x * y = y * x", False, "lp ⊭ comm"),
        ("x * y = x", "x * y = x * z", True, "lp => lp variant"),
        ("x = x", "x * y = y * x", False, "trivial_law1 ⊭ anything"),
        ("x * y = y * x", "x * y = y * x", True, "same law"),
    ]
    for law1, law2, expected, desc in test_cases:
        p = predict_implication_probability(law1, law2)
        correct = (p > 0.5) == expected
        print(f"  {desc}: p={p:.4f}, expected={'T' if expected else 'F'}, {'OK' if correct else 'WRONG'}")


if __name__ == '__main__':
    test_kb()
    test_z3()
    test_full_predictor()
