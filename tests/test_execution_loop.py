from verification.execution_loop import (
    AttemptResult,
    ExecutionOutcome,
    execute_with_recovery,
)
from verification.failure_classification import FailureClass, FailureObservation
from verification.recovery import RecoveryPolicy


def success():
    return AttemptResult(success=True, evidence={"status": "PASS"})


def simple_failure():
    return AttemptResult(
        success=False,
        observation=FailureObservation(
            test_failed=True,
            executable_fix_available=True,
        ),
    )


def drift_failure():
    return AttemptResult(
        success=False,
        observation=FailureObservation(
            test_failed=True,
            executable_fix_available=True,
            requirement_ambiguity=True,
        ),
    )


def blocked_failure():
    return AttemptResult(
        success=False,
        observation=FailureObservation(
            test_failed=True,
            verification_unavailable=True,
        ),
    )


def test_success_terminates_on_first_attempt():
    calls = []
    def attempt():
        calls.append(1)
        return success()

    result = execute_with_recovery(attempt)
    assert result.outcome is ExecutionOutcome.COMPLETE
    assert result.attempts == 1
    assert len(calls) == 1


def test_simple_failure_retries_until_success():
    sequence = iter([simple_failure(), simple_failure(), success()])
    result = execute_with_recovery(
        lambda: next(sequence),
        recovery_policy=RecoveryPolicy(max_retries=3),
    )
    assert result.outcome is ExecutionOutcome.COMPLETE
    assert result.attempts == 3


def test_retry_budget_prevents_infinite_loop():
    calls = []
    def attempt():
        calls.append(1)
        return simple_failure()

    result = execute_with_recovery(
        attempt,
        recovery_policy=RecoveryPolicy(max_retries=3),
    )
    assert result.outcome is ExecutionOutcome.USER_REQUIRED
    assert result.attempts == 4
    assert result.last_failure_class is FailureClass.SIMPLE
    assert len(calls) == 4


def test_interpretation_drift_returns_to_user_immediately():
    result = execute_with_recovery(
        drift_failure,
        recovery_policy=RecoveryPolicy(max_retries=10),
    )
    assert result.outcome is ExecutionOutcome.USER_REQUIRED
    assert result.attempts == 1
    assert result.last_failure_class is FailureClass.INTERPRETATION_DRIFT


def test_blocked_returns_to_user_immediately():
    result = execute_with_recovery(
        blocked_failure,
        recovery_policy=RecoveryPolicy(max_retries=10),
    )
    assert result.outcome is ExecutionOutcome.USER_REQUIRED
    assert result.attempts == 1
    assert result.last_failure_class is FailureClass.BLOCKED


def test_missing_failure_observation_is_fail_safe():
    result = execute_with_recovery(
        lambda: AttemptResult(success=False),
    )
    assert result.outcome is ExecutionOutcome.USER_REQUIRED
    assert result.attempts == 1


def test_multiple_failures_can_recover_without_user():
    sequence = iter([
        simple_failure(),
        simple_failure(),
        simple_failure(),
        success(),
    ])
    result = execute_with_recovery(
        lambda: next(sequence),
        recovery_policy=RecoveryPolicy(max_retries=3),
    )
    assert result.outcome is ExecutionOutcome.COMPLETE
    assert result.attempts == 4


def test_failure_after_budget_is_not_attempted_again():
    calls = 0
    def attempt():
        nonlocal calls
        calls += 1
        return simple_failure()

    result = execute_with_recovery(
        attempt,
        recovery_policy=RecoveryPolicy(max_retries=0),
    )
    assert result.outcome is ExecutionOutcome.USER_REQUIRED
    assert calls == 1
