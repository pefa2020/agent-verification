"""Deterministic executable checks for the v3.0 verification invariants."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from dfa.controller import DFAController
from dfa.events import Event
from dfa.states import State
from verification.agent_tool_runtime import AgentToolError, AgentToolRuntime, ToolRequest
from verification.evidence import EvidenceError
from verification.evidence_integrity import IntegrityError
from verification.user_intervention import UserIntervention, UserResponseKind


@dataclass(frozen=True)
class InvariantResult:
    invariant: str
    passed: bool
    detail: str


def _pass(name: str, detail: str) -> InvariantResult:
    return InvariantResult(name, True, detail)


def _check_authority() -> InvariantResult:
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    try:
        runtime.execute_tool(ToolRequest("echo", {"value": "blocked"}))
    except AgentToolError:
        return _pass("I1", "agent request was denied before verifier authorization")
    return InvariantResult("I1", False, "agent request executed without verifier authorization")


def _check_state_gate() -> InvariantResult:
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    runtime.start()
    try:
        runtime.execute_tool(ToolRequest("echo", {"value": "allowed"}))
    except AgentToolError as exc:
        return InvariantResult("I2", False, str(exc))
    return _pass("I2", "registered tool executed only after entering BUILD")


def _check_registry() -> InvariantResult:
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    runtime.start()
    try:
        runtime.execute_tool(ToolRequest("unregistered", {}))
    except AgentToolError:
        return _pass("I3", "unregistered tool was rejected")
    return InvariantResult("I3", False, "unregistered tool executed")


def _check_evidence_gate() -> InvariantResult:
    runtime = AgentToolRuntime({})
    runtime.start()
    runtime.mark_build_ready()
    payload = {
        "schema_version": "1.0",
        "status": "PASS",
        "run_id": "invariant-harness-i4",
        "commit": "deterministic-fixture",
        "criteria": {"build": "PASS", "tests": "PASS", "integration": "PASS", "smoke": "PASS"},
    }
    runtime.submit_evidence(payload)
    if runtime.state is State.COMPLETE:
        return _pass("I4", "COMPLETE was reached only through validated evidence")
    return InvariantResult("I4", False, f"unexpected final state: {runtime.state.name}")


def _check_evidence_integrity() -> InvariantResult:
    runtime = AgentToolRuntime({})
    runtime.start()
    runtime.mark_build_ready()
    payload = {
        "schema_version": "1.0",
        "status": "PASS",
        "run_id": "invariant-harness-i5",
        "commit": "deterministic-fixture",
        "criteria": {"build": "PASS", "tests": "PASS", "integration": "PASS", "smoke": "PASS"},
    }
    record = runtime.submit_evidence(payload)
    runtime.ledger._records[0] = record.__class__(
        record.run_id, record.sequence, "0" * 64, record.previous_digest, record.record_digest
    )
    if not runtime.verify_history():
        return _pass("I5", "tampered evidence history failed integrity verification")
    return InvariantResult("I5", False, "tampered evidence history remained valid")


def _check_terminal() -> InvariantResult:
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    runtime.start()
    runtime.mark_build_ready()
    runtime.controller.dispatch(Event.VERIFY_PASS)
    try:
        runtime.execute_tool(ToolRequest("echo", {"value": "after-complete"}))
    except AgentToolError:
        return _pass("I6", "tool execution was denied after COMPLETE")
    return InvariantResult("I6", False, "tool executed after COMPLETE")


def _check_user_required() -> InvariantResult:
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    runtime.start(request_valid=False)
    try:
        runtime.execute_tool(ToolRequest("echo", {"value": "autonomous"}))
    except AgentToolError:
        return _pass("I7", "USER_REQUIRED prevented autonomous tool execution")
    return InvariantResult("I7", False, "tool executed while USER_REQUIRED")


def _check_no_state_authority() -> InvariantResult:
    dfa = DFAController()
    try:
        dfa.dispatch(Event.VERIFY_PASS)
    except ValueError:
        return _pass("I8", "illegal direct state jump was rejected")
    return InvariantResult("I8", False, "DFA accepted an illegal state jump")


def _check_failure_containment() -> InvariantResult:
    runtime = AgentToolRuntime({"fail": lambda args: (_ for _ in ()).throw(RuntimeError("tool failure"))})
    runtime.start()
    result = runtime.execute_tool(ToolRequest("fail", {}))
    if not result.success and result.error == "tool failure":
        return _pass("I9", "tool exception remained an explicit failure result")
    return InvariantResult("I9", False, "tool failure was not contained")


def _check_reproducibility() -> InvariantResult:
    first = [r.passed for r in run_all()]
    second = [r.passed for r in run_all()]
    if first == second and all(first):
        return _pass("I10", "deterministic harness produced identical passing results twice")
    return InvariantResult("I10", False, "repeated deterministic run diverged or failed")


_CHECKS: tuple[Callable[[], InvariantResult], ...] = (
    _check_authority,
    _check_state_gate,
    _check_registry,
    _check_evidence_gate,
    _check_evidence_integrity,
    _check_terminal,
    _check_user_required,
    _check_no_state_authority,
    _check_failure_containment,
)


def run_all() -> list[InvariantResult]:
    return [check() for check in _CHECKS]


def main() -> int:
    results = run_all()
    results.append(_check_reproducibility())
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        print(f"{result.invariant}: {status} — {result.detail}")
    passed = sum(result.passed for result in results)
    print(f"Invariant verification: {passed}/{len(results)} passed")
    return 0 if passed == len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
