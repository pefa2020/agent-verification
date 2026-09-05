"""Verifier-owned tool registration for the v3.1 software executor."""

from __future__ import annotations

from typing import Any, Mapping

from verification.agent_tool_runtime import AgentToolRuntime
from verification.software_executor import ControlledSoftwareExecutor, ExecutionResult


SOFTWARE_TOOLS = (
    "READ_FILE",
    "WRITE_FILE",
    "CREATE_FILE",
    "DELETE_FILE",
    "RUN_TESTS",
    "RUN_BUILD",
)


def register_software_tools(
    runtime: AgentToolRuntime, executor: ControlledSoftwareExecutor
) -> None:
    """Register the fixed v3.1 executor operations with the verifier runtime.

    Registration is explicit and verifier-owned. Agent requests still pass through
    AgentToolRuntime, so its BUILD-only state gate remains authoritative.
    """
    for operation in SOFTWARE_TOOLS:
        runtime.tools[operation] = _make_tool(executor, operation)


def _make_tool(
    executor: ControlledSoftwareExecutor, operation: str
):
    def tool(arguments: Mapping[str, Any]) -> ExecutionResult:
        if not isinstance(arguments, Mapping):
            raise ValueError("tool arguments must be an object")
        try:
            return executor.execute(operation, **dict(arguments))
        except TypeError as exc:
            raise ValueError(f"malformed arguments for {operation}: {exc}") from exc

    return tool
