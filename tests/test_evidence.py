import pytest
from dfa.events import Event
from verification.evidence import EvidenceError, EvidenceStatus, evidence_to_event, validate_evidence

def payload(status="PASS", criteria=None):
    return {"schema_version":"1.0","status":status,"run_id":"build-001","commit":"abc123",
            "criteria": criteria or {"build":"PASS","tests":"PASS","integration":"PASS","smoke":"PASS"}}

def test_valid_pass():
    e=validate_evidence(payload()); assert e.status is EvidenceStatus.PASS
    assert evidence_to_event(e) is Event.VERIFY_PASS

def test_valid_fail():
    e=validate_evidence(payload("FAIL",{"build":"PASS","tests":"FAIL","integration":"PASS","smoke":"PASS"}))
    assert evidence_to_event(e) is Event.VERIFY_FAIL

def test_valid_blocked():
    e=validate_evidence(payload("BLOCKED",{"build":"PASS","tests":"BLOCKED","integration":"PASS","smoke":"PASS"}))
    assert evidence_to_event(e) is Event.VERIFY_BLOCKED

@pytest.mark.parametrize("field", ["schema_version","status","run_id","commit","criteria"])
def test_missing_required_field_rejected(field):
    d=payload(); del d[field]
    with pytest.raises(EvidenceError): validate_evidence(d)

def test_contradictory_pass_rejected():
    with pytest.raises(EvidenceError):
        validate_evidence(payload("PASS",{"build":"PASS","tests":"FAIL","integration":"PASS","smoke":"PASS"}))

def test_fail_without_failure_rejected():
    with pytest.raises(EvidenceError): validate_evidence(payload("FAIL"))

def test_blocked_without_blocked_criterion_rejected():
    with pytest.raises(EvidenceError): validate_evidence(payload("BLOCKED"))

def test_bad_schema_rejected():
    d=payload(); d["schema_version"]="999"
    with pytest.raises(EvidenceError): validate_evidence(d)

def test_bad_criterion_rejected():
    d=payload(); d["criteria"]["tests"]="MAYBE"
    with pytest.raises(EvidenceError): validate_evidence(d)
