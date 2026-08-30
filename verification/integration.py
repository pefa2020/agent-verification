from typing import Any
from .codebuild_evidence import evidence_from_codebuild
from .evidence import evidence_to_event, validate_evidence

def process_codebuild_result(
    build: dict[str, Any],
    *,
    test_status: str,
    integration_status: str,
    smoke_status: str,
):
    raw = evidence_from_codebuild(
        build,
        test_status=test_status,
        integration_status=integration_status,
        smoke_status=smoke_status,
    )
    validated = validate_evidence(raw)
    return validated, evidence_to_event(validated)
