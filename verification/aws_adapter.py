from dataclasses import dataclass
from enum import Enum

from dfa.events import Event


class AWSBuildStatus(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    FAULT = "FAULT"
    STOPPED = "STOPPED"
    TIMED_OUT = "TIMED_OUT"


@dataclass(frozen=True)
class AWSExecutionResult:
    status: AWSBuildStatus
    build_id: str
    phase_context: str = ""


def normalize_aws_result(result: AWSExecutionResult) -> Event:
    if result.status is AWSBuildStatus.SUCCEEDED:
        return Event.VERIFY_PASS

    if result.status in {
        AWSBuildStatus.FAILED,
        AWSBuildStatus.FAULT,
    }:
        return Event.VERIFY_FAIL

    # STOPPED/TIMED_OUT mean the verification run did not establish
    # correctness. The surrounding orchestration decides whether the
    # condition is a cancellation/abort or a blocked verification.
    return Event.VERIFY_BLOCKED
