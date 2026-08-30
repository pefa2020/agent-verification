from dataclasses import dataclass
from enum import Enum

class RecoveryAction(str, Enum):
    RETRY = "RETRY"
    USER_REQUIRED = "USER_REQUIRED"

class FailureClass(str, Enum):
    SIMPLE = "SIMPLE"
    INTERPRETATION_DRIFT = "INTERPRETATION_DRIFT"
    BLOCKED = "BLOCKED"

@dataclass(frozen=True)
class RecoveryDecision:
    action: RecoveryAction
    failure_count: int
    reason: str

class RecoveryPolicy:
    def __init__(self, max_retries: int = 3):
        if max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        self.max_retries = max_retries

    def decide(self, failure_class: FailureClass, failure_count: int) -> RecoveryDecision:
        if failure_count < 1:
            raise ValueError("failure_count must be >= 1")
        if failure_class in {FailureClass.INTERPRETATION_DRIFT, FailureClass.BLOCKED}:
            return RecoveryDecision(RecoveryAction.USER_REQUIRED, failure_count,
                                    f"{failure_class.value} requires user intervention")
        if failure_count <= self.max_retries:
            return RecoveryDecision(RecoveryAction.RETRY, failure_count,
                                    f"SIMPLE failure within retry budget ({failure_count}/{self.max_retries})")
        return RecoveryDecision(RecoveryAction.USER_REQUIRED, failure_count,
                                f"SIMPLE failure exceeded retry budget ({failure_count}/{self.max_retries})")
