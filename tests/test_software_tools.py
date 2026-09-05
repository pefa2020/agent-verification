from pathlib import Path
import sys

import pytest

from dfa.states import State
from verification.agent_tool_runtime import AgentToolError, AgentToolRuntime, ToolRequest
from verification.software_executor import ControlledSoftwareExecutor
from verification.software_tools import register_software_tools


@pytest.fixture
def runtime(tmp_path: Path):
    executor = ControlledSoftwareExecutor(
        tmp_path,
        test_command=(sys.executable, "-c", "print('tests-pass')"),
        build_command=(sys.executable, "-c", "print('build-pass')"),
    )
    runtime = AgentToolRuntime({})
    register_software_tools(runtime, executor)
    return runtime


def test_software_tools_are_denied_before_build(runtime):
    with pytest.raises(AgentToolError):
        runtime.execute_tool(ToolRequest("CREATE_FILE", {"path": "app.py", "content": "x"}))


def test_software_tools_execute_only_in_build(runtime):
    assert runtime.start() is State.BUILD
    result = runtime.execute_tool(
        ToolRequest("CREATE_FILE", {"path": "app.py", "content": "print('ok')\n"})
    )
    assert result.success


def test_unknown_tool_is_rejected(runtime):
    runtime.start()
    with pytest.raises(AgentToolError, match="Unknown tool"):
        runtime.execute_tool(ToolRequest("RUN_SHELL", {"command": "echo unsafe"}))


def test_terminal_state_denies_software_tools(runtime):
    runtime.start()
    runtime.mark_build_ready()
    runtime.controller.dispatch(__import__("dfa.events", fromlist=["Event"]).Event.VERIFY_PASS)
    assert runtime.state is State.COMPLETE
    with pytest.raises(AgentToolError):
        runtime.execute_tool(ToolRequest("RUN_TESTS", {}))
