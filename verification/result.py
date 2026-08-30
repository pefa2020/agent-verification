from dataclasses import dataclass, field
from enum import Enum
from typing import Any

class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"

@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    run_id: str
    commit: str
    details: dict[str, Any] = field(default_factory=dict)
