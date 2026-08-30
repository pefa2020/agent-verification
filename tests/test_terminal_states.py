from dfa.events import Event
from dfa.states import State
from dfa.transitions import transition

def test_complete_is_terminal():
    for event in Event:
        assert transition(State.COMPLETE, event) is State.COMPLETE

def test_aborted_is_terminal():
    for event in Event:
        assert transition(State.ABORTED, event) is State.ABORTED
