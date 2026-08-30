from dataclasses import dataclass
from enum import Enum

class FailureClass(str, Enum):
    SIMPLE = "SIMPLE"
    INTERPRETATION_DRIFT = "INTERPRETATION_DRIFT"
    BLOCKED = "BLOCKED"

@dataclass(frozen=True)
class FailureObservation:
    test_failed: bool
    executable_fix_available: bool = False
    requirement_ambiguity: bool = False
    repeated_same_failure: bool = False
    verification_unavailable: bool = False

class ClassificationError(ValueError):
    pass

def classify_failure(observation: FailureObservation) -> FailureClass:
    if not observation.test_failed:
        raise ClassificationError("classification requires a failed verification")
    if observation.verification_unavailable:
        return FailureClass.BLOCKED
    if observation.requirement_ambiguity:
        return FailureClass.INTERPRETATION_DRIFT
    if not observation.executable_fix_available:
        return FailureClass.INTERPRETATION_DRIFT
    return FailureClass.SIMPLE
