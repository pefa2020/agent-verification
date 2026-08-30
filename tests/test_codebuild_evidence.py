import pytest
from verification.codebuild_evidence import evidence_from_codebuild
from verification.evidence import EvidenceError, EvidenceStatus, validate_evidence

def build(status="SUCCEEDED"):
    return {"id":"agent-verification:build-001","buildStatus":status,"resolvedSourceVersion":"abc123"}

def test_success():
    e=validate_evidence(evidence_from_codebuild(build(),test_status="PASS",integration_status="PASS",smoke_status="PASS"))
    assert e.status is EvidenceStatus.PASS

def test_failure():
    e=validate_evidence(evidence_from_codebuild(build("FAILED"),test_status="PASS",integration_status="PASS",smoke_status="PASS"))
    assert e.status is EvidenceStatus.FAIL

def test_blocked():
    e=validate_evidence(evidence_from_codebuild(build("FAILED"),test_status="BLOCKED",integration_status="PASS",smoke_status="PASS"))
    assert e.status is EvidenceStatus.BLOCKED

def test_missing_id():
    d=build(); del d["id"]
    with pytest.raises(EvidenceError): evidence_from_codebuild(d,test_status="PASS",integration_status="PASS",smoke_status="PASS")

def test_missing_commit():
    d=build(); del d["resolvedSourceVersion"]
    with pytest.raises(EvidenceError): evidence_from_codebuild(d,test_status="PASS",integration_status="PASS",smoke_status="PASS")
