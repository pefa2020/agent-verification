import pytest
from dfa.events import Event
from dfa.states import State
from dfa.transitions import TRANSITIONS, transition

def test_every_defined_transition_is_deterministic():
    for (state, event), expected in TRANSITIONS.items():
        assert transition(state, event) is expected

def test_only_verify_pass_enters_complete():
    for (state, event), result in TRANSITIONS.items():
        if result is State.COMPLETE:
            assert state is State.VERIFY
            assert event is Event.VERIFY_PASS

@pytest.mark.parametrize("state,event", [
    (State.REQUEST, Event.BUILD_READY),
    (State.BUILD, Event.VERIFY_PASS),
    (State.VERIFY, Event.BUILD_READY),
    (State.USER_REQUIRED, Event.VERIFY_PASS),
])
def test_invalid_transitions_rejected(state, event):
    with pytest.raises(ValueError):
        transition(state, event)
