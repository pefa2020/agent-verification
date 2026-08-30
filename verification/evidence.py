from dataclasses import dataclass
from enum import Enum
from typing import Any
from dfa.events import Event

class EvidenceStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    BLOCKED = "BLOCKED"

REQUIRED_FIELDS = {"schema_version","status","run_id","commit","criteria"}
REQUIRED_CRITERIA = {"build","tests","integration","smoke"}

@dataclass(frozen=True)
class ValidatedEvidence:
    schema_version: str
    status: EvidenceStatus
    run_id: str
    commit: str
    criteria: dict[str, str]
    details: dict[str, Any]

class EvidenceError(ValueError):
    pass

def validate_evidence(payload: dict[str, Any]) -> ValidatedEvidence:
    if not isinstance(payload, dict):
        raise EvidenceError("Evidence must be a JSON object")
    missing = REQUIRED_FIELDS - payload.keys()
    if missing:
        raise EvidenceError(f"Missing required fields: {sorted(missing)}")
    if payload["schema_version"] != "1.0":
        raise EvidenceError("Unsupported evidence schema version")
    try:
        status = EvidenceStatus(payload["status"])
    except (ValueError, TypeError) as exc:
        raise EvidenceError("Invalid evidence status") from exc
    for field in ("run_id","commit"):
        if not isinstance(payload[field], str) or not payload[field].strip():
            raise EvidenceError(f"{field} must be a non-empty string")
    criteria = payload["criteria"]
    if not isinstance(criteria, dict):
        raise EvidenceError("criteria must be an object")
    missing_criteria = REQUIRED_CRITERIA - criteria.keys()
    if missing_criteria:
        raise EvidenceError(f"Missing mandatory criteria: {sorted(missing_criteria)}")
    for name in REQUIRED_CRITERIA:
        if criteria[name] not in {"PASS","FAIL","BLOCKED"}:
            raise EvidenceError(f"Invalid criterion status: {name}")
    if status is EvidenceStatus.PASS and any(criteria[n] != "PASS" for n in REQUIRED_CRITERIA):
        raise EvidenceError("PASS evidence contains non-PASS criteria")
    if status is EvidenceStatus.FAIL and not any(criteria[n] == "FAIL" for n in REQUIRED_CRITERIA):
        raise EvidenceError("FAIL evidence contains no failed criterion")
    if status is EvidenceStatus.BLOCKED and not any(criteria[n] == "BLOCKED" for n in REQUIRED_CRITERIA):
        raise EvidenceError("BLOCKED evidence contains no blocked criterion")
    return ValidatedEvidence(
        payload["schema_version"], status, payload["run_id"], payload["commit"],
        dict(criteria), dict(payload.get("details", {}))
    )

def evidence_to_event(evidence: ValidatedEvidence) -> Event:
    return {
        EvidenceStatus.PASS: Event.VERIFY_PASS,
        EvidenceStatus.FAIL: Event.VERIFY_FAIL,
        EvidenceStatus.BLOCKED: Event.VERIFY_BLOCKED,
    }[evidence.status]
