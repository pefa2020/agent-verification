from dfa.controller import DFAController
from dfa.events import Event
from dfa.states import State
from verification.adapter import normalize
from verification.result import VerificationResult, VerificationStatus

def result(status, attempt):
    return VerificationResult(
        status=status,
        run_id="VR-001",
        commit=f"commit-{attempt}",
        details={"attempt": attempt},
    )

def test_pass_normalization():
    assert normalize(result(VerificationStatus.PASS, 1)) is Event.VERIFY_PASS

def test_fail_normalization():
    assert normalize(result(VerificationStatus.FAIL, 1)) is Event.VERIFY_FAIL

def test_blocked_normalization():
    assert normalize(result(VerificationStatus.BLOCKED, 1)) is Event.VERIFY_BLOCKED

def test_end_to_end_repeated_failures_then_pass():
    dfa = DFAController()
    assert dfa.dispatch(Event.REQUEST_VALID) is State.BUILD
    assert dfa.dispatch(Event.BUILD_READY) is State.VERIFY

    statuses = [
        VerificationStatus.FAIL,
        VerificationStatus.FAIL,
        VerificationStatus.FAIL,
        VerificationStatus.PASS,
    ]

    for attempt, status in enumerate(statuses, 1):
        state = dfa.dispatch(normalize(result(status, attempt)))
        if status is VerificationStatus.PASS:
            assert state is State.COMPLETE
        else:
            assert state is State.BUILD
            assert dfa.dispatch(Event.BUILD_READY) is State.VERIFY

    assert dfa.accepting

def test_end_to_end_human_intervention():
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_VALID)
    dfa.dispatch(Event.BUILD_READY)
    assert dfa.dispatch(Event.VERIFY_BLOCKED) is State.USER_REQUIRED
    assert dfa.dispatch(Event.USER_RESPONSE) is State.BUILD
    assert dfa.dispatch(Event.BUILD_READY) is State.VERIFY
    assert dfa.dispatch(normalize(result(VerificationStatus.PASS, 2))) is State.COMPLETE
