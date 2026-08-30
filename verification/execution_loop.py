from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any

from .failure_classification import (
    FailureClass,
    FailureObservation,
    classify_failure,
)
from .recovery import RecoveryAction, RecoveryPolicy


class ExecutionOutcome(str, Enum):
    COMPLETE = "COMPLETE"
    USER_REQUIRED = "USER_REQUIRED"
    RETRY = "RETRY"


@dataclass(frozen=True)
class AttemptResult:
    success: bool
    observation: FailureObservation | None = None
    evidence: Any = None


@dataclass(frozen=True)
class ExecutionResult:
    outcome: ExecutionOutcome
    attempts: int
    last_failure_class: FailureClass | None = None
    reason: str = ""


def execute_with_recovery(
    attempt: Callable[[], AttemptResult],
    *,
    recovery_policy: RecoveryPolicy | None = None,
) -> ExecutionResult:
    """Execute attempts and apply classification/recovery deterministically.

    The attempt function represents one complete build/verification attempt.
    Successful verification terminates immediately. Failed verification is
    classified, then passed to the bounded recovery policy. No implicit
    retries or user prompts occur outside these rules.
    """
    policy = recovery_policy or RecoveryPolicy()
    failure_count = 0

    while True:
        result = attempt()
        if result.success:
            return ExecutionResult(
                ExecutionOutcome.COMPLETE,
                attempts=failure_count + 1,
                reason="verification passed",
            )

        if result.observation is None:
            return ExecutionResult(
                ExecutionOutcome.USER_REQUIRED,
                attempts=failure_count + 1,
                reason="failed attempt provided no failure observation",
            )

        failure_count += 1
        failure_class = classify_failure(result.observation)
        decision = policy.decide(failure_class, failure_count)

        if decision.action is RecoveryAction.RETRY:
            continue

        return ExecutionResult(
            ExecutionOutcome.USER_REQUIRED,
            attempts=failure_count,
            last_failure_class=failure_class,
            reason=decision.reason,
        )
