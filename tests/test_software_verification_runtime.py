import pytest

from dfa.states import State
from verification.agent_tool_runtime import AgentToolError, AgentToolRuntime
from verification.software_verification import (
    StepResult,
    create_evidence,
)
from verification.software_verification_evidence import verification_payload


def make_payload(build_success=True, tests_success=True):
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
        run_id="runtime-test-001",
        commit="abc123",
    )


def enter_verify(runtime):
    runtime.start()
    assert runtime.state is State.BUILD
    runtime.mark_build_ready()
    assert runtime.state is State.VERIFY


def test_v32_pass_cannot_complete_without_integration_and_smoke():
    runtime = AgentToolRuntime({})
    enter_verify(runtime)

    payload = make_payload()

    runtime.submit_evidence(payload)

    assert runtime.state is State.USER_REQUIRED
    assert runtime.verify_history() is True


def test_v32_failed_build_returns_to_build():
    runtime = AgentToolRuntime({})
    enter_verify(runtime)

    payload = make_payload(build_success=False)

    runtime.submit_evidence(payload)

    assert runtime.state is State.BUILD
    assert runtime.verify_history() is True


def test_v32_failed_tests_returns_to_build():
    runtime = AgentToolRuntime({})
    enter_verify(runtime)

    payload = make_payload(tests_success=False)

    runtime.submit_evidence(payload)

    assert runtime.state is State.BUILD
    assert runtime.verify_history() is True


def test_v32_evidence_is_replay_protected():
    runtime = AgentToolRuntime({})
    enter_verify(runtime)

    payload = make_payload()

    runtime.submit_evidence(payload)

    with pytest.raises(Exception):
        runtime.submit_evidence(payload)


def test_v32_evidence_cannot_be_submitted_outside_verify():
    runtime = AgentToolRuntime({})

    with pytest.raises(AgentToolError):
        runtime.submit_evidence(make_payload())
