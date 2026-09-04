"""Deterministic adapter for executing agent-requested tools under DFA control."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from dfa.controller import DFAController
from dfa.events import Event
from dfa.states import State
from verification.evidence import validate_evidence, evidence_to_event
from verification.evidence_integrity import EvidenceLedger, EvidenceRecord, IntegrityError


class AgentToolError(RuntimeError):
    """Raised when an agent attempts an operation outside the verification boundary."""


@dataclass(frozen=True)
class ToolRequest:
    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class ToolResult:
    success: bool
    output: Any = None
    error: str = ""


class AgentToolRuntime:
    """Small deterministic agent/tool boundary controlled by the verification DFA.

    The agent can request tools, but the runtime—not the agent—decides whether a
    request is legal. Tool calls are permitted only in BUILD, and verification
    evidence is required before the runtime can reach COMPLETE.
    """

    def __init__(self, tools: Mapping[str, Callable[[Mapping[str, Any]], Any]]):
        self.controller = DFAController()
        self.tools = dict(tools)
        self.ledger = EvidenceLedger()

    @property
    def state(self) -> State:
        return self.controller.state

    def start(self, *, request_valid: bool = True) -> State:
        event = Event.REQUEST_VALID if request_valid else Event.REQUEST_INVALID
        return self.controller.dispatch(event)

    def execute_tool(self, request: ToolRequest) -> ToolResult:
        if self.state is not State.BUILD:
            raise AgentToolError(f"Tool execution denied in state {self.state.name}")
        tool = self.tools.get(request.name)
        if tool is None:
            raise AgentToolError(f"Unknown tool: {request.name}")
        try:
            return ToolResult(True, output=tool(request.arguments))
        except Exception as exc:  # tool failures become explicit results
            return ToolResult(False, error=str(exc))

    def mark_build_ready(self) -> State:
        return self.controller.dispatch(Event.BUILD_READY)

    def submit_evidence(self, payload: dict[str, Any]) -> EvidenceRecord:
        if self.state is not State.VERIFY:
            raise AgentToolError(f"Evidence submission denied in state {self.state.name}")
        evidence = validate_evidence(payload)
        record = self.ledger.append(payload)
        self.controller.dispatch(evidence_to_event(evidence))
        return record

    def abort(self) -> State:
        return self.controller.dispatch(Event.ABORT)

    def cancel(self) -> State:
        return self.controller.dispatch(Event.CANCEL)

    def verify_history(self) -> bool:
        try:
            return self.ledger.verify()
        except IntegrityError:
            return False
