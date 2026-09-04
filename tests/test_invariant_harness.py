from verification.invariant_harness import run_all


def test_all_v3_invariants_pass():
    results = run_all()
    assert len(results) == 9
    assert all(result.passed for result in results)
    assert [result.invariant for result in results] == [
        "I1", "I2", "I3", "I4", "I5", "I6", "I7", "I8", "I9",
    ]


def test_invariant_results_are_deterministic():
    first = run_all()
    second = run_all()
    assert first == second
    assert first == second
