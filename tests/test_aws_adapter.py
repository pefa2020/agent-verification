from dfa.events import Event
from verification.aws_adapter import (
    AWSBuildStatus,
    AWSExecutionResult,
    normalize_aws_result,
)


def result(status):
    return AWSExecutionResult(
        status=status,
        build_id="aws-build-001",
        phase_context="verification",
    )


def test_aws_success_maps_to_verify_pass():
    assert normalize_aws_result(result(AWSBuildStatus.SUCCEEDED)) is Event.VERIFY_PASS


def test_aws_failure_maps_to_verify_fail():
    assert normalize_aws_result(result(AWSBuildStatus.FAILED)) is Event.VERIFY_FAIL


def test_aws_fault_maps_to_verify_fail():
    assert normalize_aws_result(result(AWSBuildStatus.FAULT)) is Event.VERIFY_FAIL


def test_aws_stopped_maps_to_verify_blocked():
    assert normalize_aws_result(result(AWSBuildStatus.STOPPED)) is Event.VERIFY_BLOCKED


def test_aws_timeout_maps_to_verify_blocked():
    assert normalize_aws_result(result(AWSBuildStatus.TIMED_OUT)) is Event.VERIFY_BLOCKED
