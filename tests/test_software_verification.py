from verification.software_verification import (
    StepResult,
    VerificationError,
    VerificationStatus,
    create_evidence,
    evidence_payload,
)


def passing_build():
    return StepResult(
        operation="RUN_BUILD",
        success=True,
        output="build pass",
        return_code=0,
    )


def passing_tests():
    return StepResult(
        operation="RUN_TESTS",
        success=True,
        output="tests pass",
        return_code=0,
    )


def test_passing_build_and_tests_produce_pass():
    evidence = create_evidence(passing_build(), passing_tests())

    assert evidence.status is VerificationStatus.PASS


def test_failed_build_produces_fail():
    build = StepResult(
        operation="RUN_BUILD",
        success=False,
        error="build failed",
        return_code=1,
    )

    evidence = create_evidence(build, passing_tests())

    assert evidence.status is VerificationStatus.FAIL


def test_failed_tests_produce_fail():
    tests = StepResult(
        operation="RUN_TESTS",
        success=False,
        error="tests failed",
        return_code=1,
    )

    evidence = create_evidence(passing_build(), tests)

    assert evidence.status is VerificationStatus.FAIL


def test_wrong_build_operation_is_rejected():
    build = StepResult(
        operation="READ_FILE",
        success=True,
    )

    try:
        create_evidence(build, passing_tests())
    except VerificationError:
        return

    raise AssertionError("invalid build operation was accepted")


def test_wrong_test_operation_is_rejected():
    tests = StepResult(
        operation="READ_FILE",
        success=True,
    )

    try:
        create_evidence(passing_build(), tests)
    except VerificationError:
        return

    raise AssertionError("invalid test operation was accepted")


def test_evidence_payload_preserves_observed_results():
    evidence = create_evidence(passing_build(), passing_tests())

    payload = evidence_payload(evidence)

    assert payload["build"]["success"] is True
    assert payload["build"]["return_code"] == 0
    assert payload["tests"]["success"] is True
    assert payload["tests"]["return_code"] == 0
    assert payload["status"] == "PASS"


def test_failure_evidence_is_not_reported_as_pass():
    tests = StepResult(
        operation="RUN_TESTS",
        success=False,
        error="failure",
        return_code=1,
    )

    evidence = create_evidence(passing_build(), tests)

    payload = evidence_payload(evidence)

    assert payload["status"] == "FAIL"
    assert payload["tests"]["success"] is False
