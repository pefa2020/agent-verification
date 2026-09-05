import pytest

from verification.agent_tool_runtime import (
    AgentToolError,
    AgentToolRuntime,
    ToolRequest,
)
from verification.aws_deployment import AWSDeploymentExecutor


class FakeAWSClient:
    def deploy(self, *, target, region, arguments):
        return {
            "success": True,
            "output": f"deployed {target} in {region}",
            "status_code": 200,
        }


def make_runtime():
    executor = AWSDeploymentExecutor(
        account_id="904557616330",
        region="us-east-1",
        target="test-environment",
        client=FakeAWSClient(),
    )

    def deploy_tool(arguments):
        result = executor.execute(
            __import__("verification.aws_deployment", fromlist=["DeploymentRequest"]).DeploymentRequest(
                operation="DEPLOY",
                target="test-environment",
                arguments=arguments,
            )
        )
        return {
            "success": result.success,
            "target": result.target,
            "account_id": result.account_id,
            "region": result.region,
            "output": result.output,
            "error": result.error,
        }

    return AgentToolRuntime({"deploy": deploy_tool})


def test_deployment_tool_is_denied_before_build():
    runtime = make_runtime()

    with pytest.raises(AgentToolError):
        runtime.execute_tool(
            ToolRequest("deploy", {"artifact": "build-001"})
        )


def test_deployment_tool_executes_only_through_build_state():
    runtime = make_runtime()

    runtime.start()

    result = runtime.execute_tool(
        ToolRequest("deploy", {"artifact": "build-001"})
    )

    assert result.success is True
    assert result.output["success"] is True
    assert result.output["target"] == "test-environment"
    assert result.output["account_id"] == "904557616330"
    assert result.output["region"] == "us-east-1"


def test_unknown_deployment_tool_is_rejected():
    runtime = make_runtime()
    runtime.start()

    with pytest.raises(AgentToolError):
        runtime.execute_tool(
            ToolRequest("deploy_aws_anything", {"target": "production"})
        )


def test_deployment_cannot_execute_after_complete():
    runtime = make_runtime()
    runtime.start()

    runtime.mark_build_ready()

    with pytest.raises(AgentToolError):
        runtime.execute_tool(
            ToolRequest("deploy", {"artifact": "build-001"})
        )


def test_deployment_cannot_execute_after_abort():
    runtime = make_runtime()
    runtime.start()

    runtime.abort()

    with pytest.raises(AgentToolError):
        runtime.execute_tool(
            ToolRequest("deploy", {"artifact": "build-001"})
        )
