from dfa.controller import DFAController
from dfa.events import Event
from dfa.states import State
from verification.aws_adapter import (
    AWSBuildStatus,
    AWSExecutionResult,
    normalize_aws_result,
)


def aws(status, build_id="aws-build-001"):
    return normalize_aws_result(
        AWSExecutionResult(status=status, build_id=build_id)
    )


def test_aws_failure_then_repair_then_success():
    dfa = DFAController()

    assert dfa.dispatch(Event.REQUEST_VALID) is State.BUILD
    assert dfa.dispatch(Event.BUILD_READY) is State.VERIFY

    assert dfa.dispatch(aws(AWSBuildStatus.FAILED)) is State.BUILD
    assert dfa.dispatch(Event.BUILD_READY) is State.VERIFY
    assert dfa.dispatch(aws(AWSBuildStatus.SUCCEEDED)) is State.COMPLETE


def test_aws_timeout_requires_human_boundary():
    dfa = DFAController()

    dfa.dispatch(Event.REQUEST_VALID)
    dfa.dispatch(Event.BUILD_READY)

    assert dfa.dispatch(aws(AWSBuildStatus.TIMED_OUT)) is State.USER_REQUIRED
    assert dfa.dispatch(Event.USER_RESPONSE) is State.BUILD
