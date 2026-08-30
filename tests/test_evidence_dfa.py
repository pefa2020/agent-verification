from dfa.controller import DFAController
from dfa.events import Event
from dfa.states import State
from verification.evidence import evidence_to_event, validate_evidence

def ev(status, tests="PASS"):
    return {"schema_version":"1.0","status":status,"run_id":"build-001","commit":"abc123",
            "criteria":{"build":"PASS","tests":tests,"integration":"PASS","smoke":"PASS"}}

def test_pass_completes():
    d=DFAController(); d.dispatch(Event.REQUEST_VALID); d.dispatch(Event.BUILD_READY)
    assert d.dispatch(evidence_to_event(validate_evidence(ev("PASS")))) is State.COMPLETE

def test_fail_returns_to_build():
    d=DFAController(); d.dispatch(Event.REQUEST_VALID); d.dispatch(Event.BUILD_READY)
    assert d.dispatch(evidence_to_event(validate_evidence(ev("FAIL","FAIL")))) is State.BUILD

def test_blocked_requires_user():
    d=DFAController(); d.dispatch(Event.REQUEST_VALID); d.dispatch(Event.BUILD_READY)
    assert d.dispatch(evidence_to_event(validate_evidence(ev("BLOCKED","BLOCKED")))) is State.USER_REQUIRED
