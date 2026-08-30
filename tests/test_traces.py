from dfa.controller import DFAController
from dfa.events import Event
from dfa.states import State

def test_success_trace():
    dfa = DFAController()
    trace = [
        Event.REQUEST_VALID,
        Event.BUILD_READY,
        Event.VERIFY_PASS,
    ]
    states = [dfa.dispatch(e) for e in trace]
    assert states == [State.BUILD, State.VERIFY, State.COMPLETE]
    assert dfa.accepting

def test_repeated_failure_trace():
    dfa = DFAController()
    trace = [
        Event.REQUEST_VALID,
        Event.BUILD_READY,
        Event.VERIFY_FAIL,
        Event.BUILD_READY,
        Event.VERIFY_FAIL,
        Event.BUILD_READY,
        Event.VERIFY_FAIL,
        Event.BUILD_READY,
        Event.VERIFY_PASS,
    ]
    states = [dfa.dispatch(e) for e in trace]
    assert states[-1] is State.COMPLETE

def test_user_clarification_trace():
    dfa = DFAController()
    trace = [
        Event.REQUEST_VALID,
        Event.BUILD_BLOCKED,
        Event.USER_RESPONSE,
        Event.BUILD_READY,
        Event.VERIFY_PASS,
    ]
    states = [dfa.dispatch(e) for e in trace]
    assert states[-1] is State.COMPLETE

def test_verification_blocked_trace():
    dfa = DFAController()
    trace = [
        Event.REQUEST_VALID,
        Event.BUILD_READY,
        Event.VERIFY_BLOCKED,
        Event.USER_RESPONSE,
        Event.BUILD_READY,
        Event.VERIFY_PASS,
    ]
    states = [dfa.dispatch(e) for e in trace]
    assert states[-1] is State.COMPLETE

def test_cancel_trace():
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_VALID)
    assert dfa.dispatch(Event.CANCEL) is State.ABORTED
    assert dfa.terminal
