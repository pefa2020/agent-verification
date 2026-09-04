import pytest

from dfa.states import State
from verification.agent_tool_runtime import AgentToolError, AgentToolRuntime, ToolRequest


def evidence(status="PASS", run_id="agent-run-1", commit="abc123", **criteria):
    values = {"build": "PASS", "tests": "PASS", "integration": "PASS", "smoke": "PASS"}
    values.update(criteria)
    return {
        "schema_version": "1.0",
        "status": status,
        "run_id": run_id,
        "commit": commit,
        "criteria": values,
    }


def test_agent_tool_call_is_allowed_only_in_build():
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    runtime.start()
    with pytest.raises(AgentToolError):
        runtime.execute_tool(ToolRequest("echo", {"value": "blocked"}))
    runtime.mark_build_ready()
    result = runtime.execute_tool(ToolRequest("echo", {"value": "allowed"}))
    assert result.success is True
    assert result.output == "allowed"


def test_unknown_tool_is_rejected_by_runtime():
    runtime = AgentToolRuntime({"echo": lambda args: args})
    runtime.start()
    with pytest.raises(AgentToolError, match="Unknown tool"):
        runtime.execute_tool(ToolRequest("delete_everything", {}))


def test_tool_failure_is_explicit_and_does_not_change_state():
    def failing(_):
        raise RuntimeError("tool failed")

    runtime = AgentToolRuntime({"fail": failing})
    runtime.start()
    result = runtime.execute_tool(ToolRequest("fail", {}))
    assert result.success is False
    assert result.error == "tool failed"
    assert runtime.state is State.BUILD


def test_evidence_submission_requires_verify_state():
    runtime = AgentToolRuntime({"echo": lambda args: args})
    runtime.start()
    with pytest.raises(AgentToolError):
        runtime.submit_evidence(evidence())


def test_passing_agent_execution_reaches_complete():
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    assert runtime.start() is State.BUILD
    result = runtime.execute_tool(ToolRequest("echo", {"value": "ok"}))
    assert result.success is True
    assert runtime.mark_build_ready() is State.VERIFY
    runtime.submit_evidence(evidence())
    assert runtime.state is State.COMPLETE
    assert runtime.controller.accepting
    assert runtime.verify_history()


def test_failed_verification_returns_to_build_without_agent_override():
    runtime = AgentToolRuntime({"echo": lambda args: args})
    runtime.start()
    runtime.mark_build_ready()
    runtime.submit_evidence(evidence(status="FAIL", criteria={"tests": "FAIL"}))
    assert runtime.state is State.BUILD


def test_blocked_verification_enters_user_required():
    runtime = AgentToolRuntime({"echo": lambda args: args})
    runtime.start()
    runtime.mark_build_ready()
    runtime.submit_evidence(evidence(status="BLOCKED", criteria={"integration": "BLOCKED"}))
    assert runtime.state is State.USER_REQUIRED


def test_terminal_complete_rejects_further_tool_execution():
    runtime = AgentToolRuntime({"echo": lambda args: args})
    runtime.start()
    runtime.mark_build_ready()
    runtime.submit_evidence(evidence())
    with pytest.raises(AgentToolError):
        runtime.execute_tool(ToolRequest("echo", {}))


def test_agent_cannot_submit_duplicate_evidence():
    runtime = AgentToolRuntime({"echo": lambda args: args})
    runtime.start()
    runtime.mark_build_ready()
    payload = evidence()
    runtime.submit_evidence(payload)
    assert runtime.state is State.COMPLETE
    with pytest.raises(AgentToolError):
        runtime.submit_evidence(payload)


def test_agent_cannot_bypass_dfa_with_direct_tool_request():
    runtime = AgentToolRuntime({"echo": lambda args: args})
    with pytest.raises(AgentToolError):
        runtime.execute_tool(ToolRequest("echo", {}))
    assert runtime.state is State.REQUEST


def test_abort_is_terminal_and_blocks_tools():
    runtime = AgentToolRuntime({"echo": lambda args: args})
    runtime.start()
    assert runtime.abort() is State.ABORTED
    with pytest.raises(AgentToolError):
        runtime.execute_tool(ToolRequest("echo", {}))
