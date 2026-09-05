from verification.aws_deployment_invariants import INVARIANTS, run_invariants


def test_all_v3_3_deployment_invariants_pass():
    results = run_invariants()

    assert set(results) == set(INVARIANTS)
    assert all(results.values())


def test_each_v3_3_invariant_passes_individually():
    results = run_invariants()

    for name, passed in results.items():
        assert passed, f"{name} invariant failed"
