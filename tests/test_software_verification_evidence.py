import pytest

from verification.software_verification import (
    StepResult,
    VerificationStatus,
    create_evidence,
)
from verification.software_verification_evidence import verification_payload


def make_evidence(build_success=True, tests_success=True):
    build = StepResult(
        operation="RUN_BUILD",
        success=build_success,
        output="build output",
        error="" if build_success else "build failed",
        return_code=0 if build_success else 1,
    )
    tests = StepResult(
        operation="RUN_TESTS",
        success=tests_success,
        output="test output",
        error="" if tests_success else "tests failed",
        return_code=0 if tests_success else 1,
    )
    return create_evidence(build, tests)


def test_passing_build_and_tests_are_blocked_until_integration_and_smoke_exist():
    evidence = make_evidence()

    payload = verification_payload(
        evidence,
        run_id="run-001",
        commit="abc123",
    )

    assert evidence.status is VerificationStatus.PASS
    assert payload["status"] == "BLOCKED"
    assert payload["criteria"] == {
        "build": "PASS",
        "tests": "PASS",
        "integration": "BLOCKED",
        "smoke": "BLOCKED",
    }


def test_failed_build_becomes_fail_evidence():
    evidence = make_evidence(build_success=False)

    payload = verification_payload(
        evidence,
        run_id="run-002",
        commit="abc123",
    )

    assert payload["status"] == "FAIL"
    assert payload["criteria"]["build"] == "FAIL"
    assert payload["criteria"]["tests"] == "PASS"


def test_failed_tests_become_fail_evidence():
    evidence = make_evidence(tests_success=False)

    payload = verification_payload(
        evidence,
        run_id="run-003",
        commit="abc123",
    )

    assert payload["status"] == "FAIL"
    assert payload["criteria"]["build"] == "PASS"
    assert payload["criteria"]["tests"] == "FAIL"


def test_execution_details_are_preserved():
    evidence = make_evidence()

    payload = verification_payload(
        evidence,
        run_id="run-004",
        commit="deadbeef",
    )

    assert payload["run_id"] == "run-004"
    assert payload["commit"] == "deadbeef"
    assert payload["details"]["build"]["operation"] == "RUN_BUILD"
    assert payload["details"]["tests"]["operation"] == "RUN_TESTS"
    assert payload["details"]["build"]["return_code"] == 0
    assert payload["details"]["tests"]["return_code"] == 0


def test_payload_is_accepted_by_existing_verifier_contract():
    from verification.evidence import validate_evidence

    payload = verification_payload(
        make_evidence(),
        run_id="run-005",
        commit="abc123",
    )

    validated = validate_evidence(payload)

    assert validated.status.value == "BLOCKED"
    assert validated.run_id == "run-005"
    assert validated.commit == "abc123"
