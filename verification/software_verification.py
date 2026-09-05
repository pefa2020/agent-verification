"""Deterministic software build/test verification for v3.2."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class VerificationError(ValueError):
    """Raised when verification evidence is malformed."""


class VerificationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"


@dataclass(frozen=True)
class StepResult:
    operation: str
    success: bool
    output: str = ""
    error: str = ""
    return_code: int | None = None


@dataclass(frozen=True)
class VerificationEvidence:
    build: StepResult
    tests: StepResult

    @property
    def status(self) -> VerificationStatus:
        if not self.build.success or not self.tests.success:
            return VerificationStatus.FAIL
        return VerificationStatus.PASS


def create_evidence(
    build: StepResult,
    tests: StepResult,
) -> VerificationEvidence:
    if build.operation != "RUN_BUILD":
        raise VerificationError("build result must be RUN_BUILD")

    if tests.operation != "RUN_TESTS":
        raise VerificationError("test result must be RUN_TESTS")

    return VerificationEvidence(build=build, tests=tests)


def evidence_payload(evidence: VerificationEvidence) -> dict[str, Any]:
    return {
        "build": {
            "operation": evidence.build.operation,
            "success": evidence.build.success,
            "output": evidence.build.output,
            "error": evidence.build.error,
            "return_code": evidence.build.return_code,
        },
        "tests": {
            "operation": evidence.tests.operation,
            "success": evidence.tests.success,
            "output": evidence.tests.output,
            "error": evidence.tests.error,
            "return_code": evidence.tests.return_code,
        },
        "status": evidence.status.value,
    }
