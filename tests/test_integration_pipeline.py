from dfa.controller import DFAController
from dfa.events import Event
from dfa.states import State
from verification.integration import process_codebuild_result

def build(status="SUCCEEDED", commit="abc123"):
    return {
        "id": "agent-verification:integration-001",
        "buildStatus": status,
        "resolvedSourceVersion": commit,
    }

def test_realistic_success_path_maps_to_complete():
    evidence, event = process_codebuild_result(
        build(), test_status="PASS", integration_status="PASS", smoke_status="PASS"
    )
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_VALID)
    dfa.dispatch(Event.BUILD_READY)
    assert event is Event.VERIFY_PASS
    assert dfa.dispatch(event) is State.COMPLETE
    assert evidence.run_id.startswith("agent-verification:")

def test_realistic_failure_path_maps_back_to_build():
    evidence, event = process_codebuild_result(
        build("FAILED"), test_status="PASS", integration_status="PASS", smoke_status="PASS"
    )
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_VALID)
    dfa.dispatch(Event.BUILD_READY)
    assert event is Event.VERIFY_FAIL
    assert dfa.dispatch(event) is State.BUILD

def test_repeated_failure_then_success_is_deterministic():
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_VALID)
    dfa.dispatch(Event.BUILD_READY)

    _, event1 = process_codebuild_result(
        build("FAILED", "commit-1"), test_status="FAIL",
        integration_status="PASS", smoke_status="PASS"
    )
    assert dfa.dispatch(event1) is State.BUILD

    dfa.dispatch(Event.BUILD_READY)
    _, event2 = process_codebuild_result(
        build("SUCCEEDED", "commit-2"), test_status="PASS",
        integration_status="PASS", smoke_status="PASS"
    )
    assert dfa.dispatch(event2) is State.COMPLETE

def test_blocked_evidence_stops_at_user_required():
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_VALID)
    dfa.dispatch(Event.BUILD_READY)

    _, event = process_codebuild_result(
        build(), test_status="BLOCKED",
        integration_status="PASS", smoke_status="PASS"
    )
    assert dfa.dispatch(event) is State.USER_REQUIRED
