import pytest

from dfa.states import State
from verification.agent_tool_runtime import AgentToolError, AgentToolRuntime
from verification.software_verification import (
    StepResult,
    create_evidence,
)
from verification.software_verification_evidence import verification_payload


def make_payload(
    *,
    build_success=True,
    tests_success=True,
    run_id="adversarial-001",
):
    evidence = create_evidence(
        StepResult(
            operation="RUN_BUILD",
            success=build_success,
            output="build output",
            error="" if build_success else "build failed",
            return_code=0 if build_success else 1,
        ),
        StepResult(
            operation="RUN_TESTS",
            success=tests_success,
            output="test output",
            error="" if tests_success else "tests failed",
            return_code=0 if tests_success else 1,
        ),
    )

    return verification_payload(
        evidence,
        run_id=run_id,
        commit="abc123",
    )


def enter_verify(runtime):
    runtime.start()
    assert runtime.state is State.BUILD
    runtime.mark_build_ready()
    assert runtime.state is State.VERIFY


def test_forged_pass_with_blocked_criteria_cannot_reach_complete():
    runtime = AgentToolRuntime({})
    enter_verify(runtime)

    payload = make_payload()
    payload["status"] = "PASS"

    with pytest.raises(Exception):
        runtime.submit_evidence(payload)

    assert runtime.state is State.VERIFY


def test_forged_pass_after_failed_build_is_rejected():
    runtime = AgentToolRuntime({})
    enter_verify(runtime)

    payload = make_payload(build_success=False)
    payload["status"] = "PASS"

    with pytest.raises(Exception):
        runtime.submit_evidence(payload)

    assert runtime.state is State.VERIFY


def test_forged_pass_after_failed_tests_is_rejected():
    runtime = AgentToolRuntime({})
    enter_verify(runtime)

    payload = make_payload(tests_success=False)
    payload["status"] = "PASS"

    with pytest.raises(Exception):
        runtime.submit_evidence(payload)

    assert runtime.state is State.VERIFY


def test_mutated_evidence_after_creation_is_rejected():
    runtime = AgentToolRuntime({})
    enter_verify(runtime)

    payload = make_payload()
    runtime.submit_evidence(payload)

    mutated = dict(payload)
    mutated["run_id"] = "different-run"

    with pytest.raises(Exception):
        runtime.submit_evidence(mutated)


def test_duplicate_run_id_with_different_evidence_is_allowed_by_current_ledger():
    runtime = AgentToolRuntime({})
    enter_verify(runtime)

    first = make_payload(
        build_success=False,
        run_id="same-run",
    )
    runtime.submit_evidence(first)

    assert runtime.state is State.BUILD

    runtime.mark_build_ready()
    assert runtime.state is State.VERIFY

    second = make_payload(
        tests_success=False,
        run_id="same-run",
    )
    runtime.submit_evidence(second)

    assert runtime.state is State.BUILD


def test_agent_cannot_submit_evidence_and_continue_after_user_required():
    runtime = AgentToolRuntime({})
    enter_verify(runtime)

    runtime.submit_evidence(make_payload())

    assert runtime.state is State.USER_REQUIRED

    with pytest.raises(AgentToolError):
        runtime.execute_tool(
            type("Request", (), {
                "name": "anything",
                "arguments": {},
            })()
        )
