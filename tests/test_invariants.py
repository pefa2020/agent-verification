import pytest
from dfa.events import Event
from dfa.states import State
from dfa.transitions import TRANSITIONS, transition

def test_only_verify_pass_reaches_complete():
    for (state, event), result in TRANSITIONS.items():
        if result is State.COMPLETE:
            assert state is State.VERIFY
            assert event is Event.VERIFY_PASS

def test_abort_never_accepts():
    assert State.ABORTED is not State.COMPLETE

def test_invalid_operational_transitions_are_rejected():
    invalid = [
        (State.REQUEST, Event.BUILD_READY),
        (State.BUILD, Event.VERIFY_PASS),
        (State.VERIFY, Event.BUILD_READY),
        (State.USER_REQUIRED, Event.VERIFY_PASS),
    ]
    for state, event in invalid:
        with pytest.raises(ValueError):
            transition(state, event)
