"""Convert observed AWS deployment results into existing verifier evidence."""

from __future__ import annotations

from typing import Any

from verification.aws_deployment import DeploymentResult


def deployment_evidence_payload(
    result: DeploymentResult,
    *,
    run_id: str,
    commit: str,
) -> dict[str, Any]:
    """Build verifier evidence from an executor-observed deployment result."""

    return {
        "schema_version": "1.0",
        "status": "PASS" if result.success else "FAIL",
        "run_id": run_id,
        "commit": commit,
        "criteria": {
            "build": "BLOCKED",
            "tests": "BLOCKED",
            "integration": "BLOCKED",
            "smoke": "BLOCKED",
            "deployment": "PASS" if result.success else "FAIL",
        },
        "details": {
            "deployment": {
                "operation": result.operation,
                "success": result.success,
                "target": result.target,
                "account_id": result.account_id,
                "region": result.region,
                "output": result.output,
                "error": result.error,
                "status_code": result.status_code,
            }
        },
    }
