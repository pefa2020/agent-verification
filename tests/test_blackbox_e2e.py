from verification.controlled_execution import ControlledExecution, ControlledOutcome
from verification.execution_loop import AttemptResult
from verification.failure_classification import FailureObservation, FailureClass
from verification.recovery import RecoveryPolicy
from verification.user_intervention import UserIntervention, UserResponseKind


def run_external(outcomes, responses=None, retries=3):
    sequence = iter(outcomes)
    engine = ControlledExecution(
        lambda: next(sequence),
        RecoveryPolicy(max_retries=retries),
    )
    return engine.run(responses)


def success():
    return AttemptResult(success=True)


def simple_fail():
    return AttemptResult(
        success=False,
        observation=FailureObservation(
            test_failed=True,
            executable_fix_available=True,
        ),
    )


def drift_fail():
    return AttemptResult(
        success=False,
        observation=FailureObservation(
            test_failed=True,
            executable_fix_available=True,
            requirement_ambiguity=True,
        ),
    )


def blocked():
    return AttemptResult(
        success=False,
        observation=FailureObservation(
            test_failed=True,
            verification_unavailable=True,
        ),
    )


def test_external_success():
    result = run_external([success()])
    assert result.outcome is ControlledOutcome.COMPLETE
    assert result.attempts == 1


def test_external_simple_failure_recovers():
    result = run_external([simple_fail(), success()])
    assert result.outcome is ControlledOutcome.COMPLETE
    assert result.attempts == 2


def test_external_repeated_failure_is_bounded():
    result = run_external([simple_fail(), simple_fail(), simple_fail(), simple_fail()])
    assert result.outcome is ControlledOutcome.USER_REQUIRED
    assert result.attempts == 4
    assert result.failure_classes == (
        FailureClass.SIMPLE,
        FailureClass.SIMPLE,
        FailureClass.SIMPLE,
        FailureClass.SIMPLE,
    )


def test_external_drift_requires_user():
    result = run_external(
        [drift_fail(), success()],
        [UserIntervention(UserResponseKind.CLARIFICATION, "Correct objective")],
    )
    assert result.outcome is ControlledOutcome.COMPLETE
    assert result.attempts == 2
    assert result.clarifications == 1


def test_external_blocked_requires_user():
    result = run_external(
        [blocked()],
        [UserIntervention(UserResponseKind.CANCEL)],
    )
    assert result.outcome is ControlledOutcome.ABORTED
    assert result.attempts == 1


def test_external_user_can_abort_after_drift():
    result = run_external(
        [drift_fail()],
        [UserIntervention(UserResponseKind.ABORT)],
    )
    assert result.outcome is ControlledOutcome.ABORTED


def test_external_clarification_preserves_history():
    result = run_external(
        [drift_fail(), simple_fail(), success()],
        [UserIntervention(UserResponseKind.CLARIFICATION, "Clarify")],
    )
    assert result.outcome is ControlledOutcome.COMPLETE
    assert result.failure_classes == (
        FailureClass.INTERPRETATION_DRIFT,
        FailureClass.SIMPLE,
    )
    assert result.attempts == 3


def test_external_no_user_response_stops_at_boundary():
    result = run_external([drift_fail()])
    assert result.outcome is ControlledOutcome.USER_REQUIRED
    assert result.attempts == 1
