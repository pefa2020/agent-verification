import pytest

from dfa.controller import DFAController
from dfa.events import Event
from dfa.states import State
from dfa.transitions import TRANSITIONS
from verification.evidence import EvidenceError, validate_evidence


ALL_EVENTS = tuple(Event)
NON_TERMINAL_STATES = (State.REQUEST, State.BUILD, State.VERIFY, State.USER_REQUIRED)


def payload():
    return {
        "schema_version": "1.0",
        "status": "PASS",
        "run_id": "build-001",
        "commit": "abc123",
        "criteria": {
            "build": "PASS",
            "tests": "PASS",
            "integration": "PASS",
            "smoke": "PASS",
        },
    }


@pytest.mark.parametrize("state", (State.COMPLETE, State.ABORTED))
def test_terminal_states_absorb_every_event(state):
    dfa = DFAController(state)
    for event in ALL_EVENTS:
        assert dfa.dispatch(event) is state
    assert dfa.terminal


@pytest.mark.parametrize("state", NON_TERMINAL_STATES)
def test_undefined_non_terminal_transitions_are_rejected(state):
    for event in ALL_EVENTS:
        if (state, event) not in TRANSITIONS:
            dfa = DFAController(state)
            with pytest.raises(ValueError, match="Invalid transition"):
                dfa.dispatch(event)
            assert dfa.state is state


@pytest.mark.parametrize("field,value", [
    ("run_id", ""),
    ("run_id", "   "),
    ("run_id", 123),
    ("commit", ""),
    ("commit", "   "),
    ("commit", 123),
])
def test_malformed_identifiers_are_rejected(field, value):
    data = payload()
    data[field] = value
    with pytest.raises(EvidenceError):
        validate_evidence(data)


@pytest.mark.parametrize("field,value", [
    ("schema_version", None),
    ("status", None),
    ("criteria", None),
    ("criteria", []),
    ("criteria", "PASS"),
])
def test_malformed_evidence_field_types_are_rejected(field, value):
    data = payload()
    data[field] = value
    with pytest.raises(EvidenceError):
        validate_evidence(data)


def test_non_object_evidence_is_rejected():
    with pytest.raises(EvidenceError):
        validate_evidence([])


def test_terminal_completion_cannot_be_reopened():
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_VALID)
    dfa.dispatch(Event.BUILD_READY)
    dfa.dispatch(Event.VERIFY_PASS)
    assert dfa.state is State.COMPLETE

    for event in ALL_EVENTS:
        assert dfa.dispatch(event) is State.COMPLETE


def test_terminal_abort_cannot_be_reopened():
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_INVALID)
    dfa.dispatch(Event.ABORT)
    assert dfa.state is State.ABORTED

    for event in ALL_EVENTS:
        assert dfa.dispatch(event) is State.ABORTED
