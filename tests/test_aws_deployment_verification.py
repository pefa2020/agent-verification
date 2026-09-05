import pytest

from dfa.events import Event
from verification.agent_tool_runtime import AgentToolError, AgentToolRuntime
from verification.aws_deployment import AWSDeploymentExecutor, DeploymentRequest
from verification.aws_deployment_evidence import deployment_evidence_payload


class FakeAWSClient:
    def deploy(self, *, target, region, arguments):
        return {
            "success": True,
            "output": "deployment completed",
            "status_code": 200,
        }


def make_executor():
    return AWSDeploymentExecutor(
        account_id="904557616330",
        region="us-east-1",
        target="test-environment",
        client=FakeAWSClient(),
    )


def test_deployment_evidence_is_validated_by_existing_boundary():
    runtime = AgentToolRuntime({})
    executor = make_executor()

    runtime.start()

    # Deployment itself does not replace the software-verification lifecycle.
    result = executor.execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={"artifact": "build-001"},
        )
    )

    payload = deployment_evidence_payload(
        result,
        run_id="deployment-run-001",
        commit="abc123",
    )

    assert payload["status"] == "PASS"
    assert payload["criteria"]["build"] == "BLOCKED"
    assert payload["criteria"]["tests"] == "BLOCKED"

    with pytest.raises(AgentToolError):
        runtime.submit_evidence(payload)


def test_deployment_evidence_cannot_claim_full_verification():
    runtime = AgentToolRuntime({})
    executor = make_executor()

    runtime.start()
    runtime.mark_build_ready()

    result = executor.execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={},
        )
    )

    payload = deployment_evidence_payload(
        result,
        run_id="deployment-run-002",
        commit="abc123",
    )

    with pytest.raises(ValueError, match="PASS evidence contains non-PASS criteria"):
        runtime.submit_evidence(payload)


def test_failed_deployment_remains_failure_evidence():
    class FailingAWSClient:
        def deploy(self, *, target, region, arguments):
            return {
                "success": False,
                "error": "deployment failed",
                "status_code": 500,
            }

    executor = AWSDeploymentExecutor(
        account_id="904557616330",
        region="us-east-1",
        target="test-environment",
        client=FailingAWSClient(),
    )

    result = executor.execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={},
        )
    )

    payload = deployment_evidence_payload(
        result,
        run_id="deployment-run-003",
        commit="abc123",
    )

    assert payload["status"] == "FAIL"
    assert payload["criteria"]["deployment"] == "FAIL"
