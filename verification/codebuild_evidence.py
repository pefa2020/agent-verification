from typing import Any
from .evidence import EvidenceError, EvidenceStatus

def evidence_from_codebuild(build: dict[str, Any], *, test_status: str,
                            integration_status: str, smoke_status: str) -> dict[str, Any]:
    if not isinstance(build, dict):
        raise EvidenceError("CodeBuild payload must be an object")
    build_id = build.get("id")
    commit = build.get("resolvedSourceVersion") or build.get("sourceVersion") or ""
    build_status = build.get("buildStatus")
    if not build_id or not commit:
        raise EvidenceError("CodeBuild payload lacks build id or commit")
    criteria = {
        "build": "PASS" if build_status == "SUCCEEDED" else "FAIL",
        "tests": test_status,
        "integration": integration_status,
        "smoke": smoke_status,
    }
    if any(v == "BLOCKED" for v in criteria.values()):
        status = EvidenceStatus.BLOCKED.value
    elif any(v == "FAIL" for v in criteria.values()):
        status = EvidenceStatus.FAIL.value
    else:
        status = EvidenceStatus.PASS.value
    return {
        "schema_version": "1.0", "status": status, "run_id": build_id,
        "commit": commit, "criteria": criteria,
        "details": {"provider": "aws-codebuild", "build_status": build_status},
    }
