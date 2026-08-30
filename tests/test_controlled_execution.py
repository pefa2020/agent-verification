from verification.controlled_execution import ControlledExecution, ControlledOutcome
from verification.execution_loop import AttemptResult
from verification.failure_classification import FailureObservation, FailureClass
from verification.recovery import RecoveryPolicy
from verification.user_intervention import UserIntervention, UserResponseKind


def fail_simple():
    return AttemptResult(False, FailureObservation(True, executable_fix_available=True))


def fail_drift():
    return AttemptResult(False, FailureObservation(True, executable_fix_available=True, requirement_ambiguity=True))


def success():
    return AttemptResult(True)


def test_failure_clarification_failure_then_success():
    sequence = iter([fail_drift(), fail_simple(), success()])
    engine = ControlledExecution(lambda: next(sequence), RecoveryPolicy(3))
    result = engine.run([
        UserIntervention(UserResponseKind.CLARIFICATION, "Clarify requirement")
    ])
    assert result.outcome is ControlledOutcome.COMPLETE
    assert result.attempts == 3
    assert result.clarifications == 1
    assert result.failure_classes == (
        FailureClass.INTERPRETATION_DRIFT, FailureClass.SIMPLE
    )


def test_clarification_does_not_reset_history_or_attempt_count():
    sequence = iter([fail_drift(), success()])
    engine = ControlledExecution(lambda: next(sequence), RecoveryPolicy(3))
    result = engine.run([
        UserIntervention(UserResponseKind.CLARIFICATION, "Corrected objective")
    ])
    assert result.attempts == 2
    assert result.clarifications == 1
    assert result.failure_classes == (FailureClass.INTERPRETATION_DRIFT,)


def test_cancel_after_user_required_is_terminal():
    engine = ControlledExecution(fail_drift)
    result = engine.run([UserIntervention(UserResponseKind.CANCEL)])
    assert result.outcome is ControlledOutcome.ABORTED
    assert result.state.name == "ABORTED"


def test_abort_after_user_required_is_terminal():
    engine = ControlledExecution(fail_drift)
    result = engine.run([UserIntervention(UserResponseKind.ABORT)])
    assert result.outcome is ControlledOutcome.ABORTED


def test_simple_failures_can_retry_then_clarification_after_exhaustion():
    sequence = iter([fail_simple(), fail_simple(), success()])
    engine = ControlledExecution(lambda: next(sequence), RecoveryPolicy(1))
    result = engine.run([
        UserIntervention(UserResponseKind.CLARIFICATION, "Try a different approach")
    ])
    assert result.outcome is ControlledOutcome.COMPLETE
    assert result.attempts == 3
    assert result.clarifications == 1
    assert result.failure_classes == (FailureClass.SIMPLE, FailureClass.SIMPLE)


def test_user_required_without_response_does_not_auto_continue():
    engine = ControlledExecution(fail_drift)
    result = engine.run()
    assert result.outcome is ControlledOutcome.USER_REQUIRED
    assert result.state.name == "USER_REQUIRED"
    assert result.attempts == 1
