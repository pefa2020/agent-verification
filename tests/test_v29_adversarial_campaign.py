import json

import pytest

from dfa.controller import DFAController
from dfa.events import Event
from dfa.states import State
from verification.agent_tool_runtime import AgentToolError, AgentToolRuntime, ToolRequest
from verification.evidence import EvidenceError, validate_evidence
from verification.evidence_integrity import EvidenceLedger, IntegrityError, evidence_digest
from verification.llm_agent_runtime import LLMIntegrationError, OpenAILLMAdapter


def evidence(status="PASS", run_id="run-1", commit="abc123", criteria=None):
    values = {"build": "PASS", "tests": "PASS", "integration": "PASS", "smoke": "PASS"}
    if criteria:
        values.update(criteria)
    return {
        "schema_version": "1.0",
        "status": status,
        "run_id": run_id,
        "commit": commit,
        "criteria": values,
    }


class FakeFunctionCall:
    type = "function_call"

    def __init__(self, name, arguments, call_id="call-1"):
        self.name = name
        self.arguments = arguments
        self.call_id = call_id


class FakeResponse:
    def __init__(self, output, response_id="resp-1", text="done"):
        self.output = output
        self.id = response_id
        self.output_text = text


class FakeResponses:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.responses)


class FakeClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


def test_model_cannot_execute_unknown_tool_even_when_call_is_well_formed():
    client = FakeClient([
        FakeResponse([FakeFunctionCall("not_registered", json.dumps({"value": "x"}))]),
        FakeResponse([], response_id="resp-2"),
    ])
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    _, transcript = OpenAILLMAdapter(runtime, client=client).run("request unavailable tool")
    assert transcript[0]["allowed"] is False
    assert "Unknown tool" in transcript[0]["error"]


def test_malformed_model_json_never_reaches_tool():
    called = False

    def tool(_):
        nonlocal called
        called = True
        return "should-not-run"

    client = FakeClient([FakeResponse([FakeFunctionCall("echo", "{not-json")])])
    runtime = AgentToolRuntime({"echo": tool})
    with pytest.raises(LLMIntegrationError, match="invalid JSON"):
        OpenAILLMAdapter(runtime, client=client).run("malformed")
    assert called is False


def test_non_object_model_arguments_never_reach_tool():
    called = False

    def tool(_):
        nonlocal called
        called = True
        return "should-not-run"

    client = FakeClient([FakeResponse([FakeFunctionCall("echo", "[]")])])
    runtime = AgentToolRuntime({"echo": tool})
    with pytest.raises(LLMIntegrationError, match="JSON object"):
        OpenAILLMAdapter(runtime, client=client).run("wrong shape")
    assert called is False


def test_tool_exception_becomes_failed_result_without_state_change():
    def failing(_):
        raise RuntimeError("controlled failure")

    runtime = AgentToolRuntime({"fail": failing})
    runtime.start()
    result = runtime.execute_tool(ToolRequest("fail", {}))
    assert result.success is False
    assert result.error == "controlled failure"
    assert runtime.state is State.BUILD


def test_denied_tool_request_cannot_mutate_runtime_state():
    runtime = AgentToolRuntime({"echo": lambda args: args})
    assert runtime.state is State.REQUEST
    with pytest.raises(AgentToolError):
        runtime.execute_tool(ToolRequest("echo", {"value": "x"}))
    assert runtime.state is State.REQUEST


@pytest.mark.parametrize("terminal", [State.COMPLETE, State.ABORTED])
def test_terminal_runtime_states_reject_tools(terminal):
    runtime = AgentToolRuntime({"echo": lambda args: args})
    if terminal is State.COMPLETE:
        runtime.start()
        runtime.mark_build_ready()
        runtime.submit_evidence(evidence())
    else:
        runtime.start()
        runtime.abort()
    with pytest.raises(AgentToolError, match="denied"):
        runtime.execute_tool(ToolRequest("echo", {"value": "x"}))
    assert runtime.state is terminal


def test_fail_then_retry_keeps_agent_inside_build_boundary():
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    runtime.start()
    runtime.mark_build_ready()
    runtime.submit_evidence(evidence(status="FAIL", criteria={"tests": "FAIL"}))
    assert runtime.state is State.BUILD
    result = runtime.execute_tool(ToolRequest("echo", {"value": "retry"}))
    assert result.success is True
    assert runtime.state is State.BUILD


def test_blocked_verification_prevents_autonomous_tool_continuation():
    runtime = AgentToolRuntime({"echo": lambda args: args})
    runtime.start()
    runtime.mark_build_ready()
    runtime.submit_evidence(evidence(status="BLOCKED", criteria={"integration": "BLOCKED"}))
    assert runtime.state is State.USER_REQUIRED
    with pytest.raises(AgentToolError):
        runtime.execute_tool(ToolRequest("echo", {}))


def test_replayed_evidence_is_rejected_before_second_record():
    runtime = AgentToolRuntime({"echo": lambda args: args})
    runtime.start()
    runtime.mark_build_ready()
    payload = evidence()
    runtime.submit_evidence(payload)
    assert len(runtime.ledger.records) == 1
    with pytest.raises(AgentToolError):
        runtime.submit_evidence(payload)
    assert len(runtime.ledger.records) == 1
    assert runtime.verify_history()


def test_mutated_evidence_cannot_reuse_original_digest():
    original = evidence()
    mutated = dict(original)
    mutated["commit"] = "attacker-controlled"
    assert evidence_digest(original) != evidence_digest(mutated)


def test_tampered_ledger_record_is_detected():
    ledger = EvidenceLedger()
    first = ledger.append(evidence(run_id="run-1"))
    second = ledger.append(evidence(run_id="run-2"))
    ledger._records = [
        first.__class__(first.run_id, first.sequence, "f" * 64, first.previous_digest, first.record_digest),
        second,
    ]
    assert ledger.verify() is False


def test_reordered_ledger_history_is_detected():
    ledger = EvidenceLedger()
    first = ledger.append(evidence(run_id="run-1"))
    second = ledger.append(evidence(run_id="run-2"))
    ledger._records = [second, first]
    assert ledger.verify() is False


def test_duplicate_sequence_in_ledger_is_detected():
    ledger = EvidenceLedger()
    first = ledger.append(evidence(run_id="run-1"))
    second = ledger.append(evidence(run_id="run-2"))
    ledger._records = [
        first,
        second.__class__(second.run_id, first.sequence, second.evidence_digest, second.previous_digest, second.record_digest),
    ]
    assert ledger.verify() is False


def test_malformed_evidence_cannot_become_a_verification_event():
    data = evidence()
    data["criteria"] = "PASS"
    with pytest.raises(EvidenceError):
        validate_evidence(data)


def test_invalid_dfa_event_cannot_be_used_to_jump_from_build_to_complete():
    dfa = DFAController()
    dfa.dispatch(Event.REQUEST_VALID)
    assert dfa.state is State.BUILD
    with pytest.raises(ValueError, match="Invalid transition"):
        dfa.dispatch(Event.VERIFY_PASS)
    assert dfa.state is State.BUILD


def test_invalid_dfa_event_cannot_be_used_to_jump_from_request_to_complete():
    dfa = DFAController()
    with pytest.raises(ValueError, match="Invalid transition"):
        dfa.dispatch(Event.VERIFY_PASS)
    assert dfa.state is State.REQUEST


def test_complete_is_absorbing_after_agent_tool_and_evidence_sequence():
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    runtime.start()
    runtime.execute_tool(ToolRequest("echo", {"value": "ok"}))
    runtime.mark_build_ready()
    runtime.submit_evidence(evidence())
    assert runtime.state is State.COMPLETE
    assert runtime.controller.accepting
    assert runtime.verify_history()
    with pytest.raises(AgentToolError):
        runtime.execute_tool(ToolRequest("echo", {"value": "late"}))


def test_model_error_feedback_does_not_grant_unknown_tool_authority():
    client = FakeClient([
        FakeResponse([FakeFunctionCall("unknown", "{}")]),
        FakeResponse([], response_id="resp-2", text="I received a verifier error."),
    ])
    runtime = AgentToolRuntime({"echo": lambda args: args})
    output, transcript = OpenAILLMAdapter(runtime, client=client).run("try unavailable tool")
    assert "verifier error" in output
    assert transcript[0]["allowed"] is False
    assert runtime.state is State.BUILD
