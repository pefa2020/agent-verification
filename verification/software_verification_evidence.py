"""Convert observed v3.2 execution results into existing verifier evidence."""

from __future__ import annotations

from typing import Any

from verification.software_verification import VerificationEvidence


def verification_payload(
    evidence: VerificationEvidence,
    *,
    run_id: str,
    commit: str,
) -> dict[str, Any]:
    """Build verifier evidence from executor-observed build/test results."""

    return {
        "schema_version": "1.0",
        "status": "BLOCKED"
        if evidence.status.value == "PASS"
        else evidence.status.value,
        "run_id": run_id,
        "commit": commit,
        "criteria": {
            "build": "PASS" if evidence.build.success else "FAIL",
            "tests": "PASS" if evidence.tests.success else "FAIL",
            "integration": "BLOCKED",
            "smoke": "BLOCKED",
        },
        "details": {
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
        },
    }
