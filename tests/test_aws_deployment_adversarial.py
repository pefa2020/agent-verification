import pytest

from verification.agent_tool_runtime import AgentToolError, AgentToolRuntime, ToolRequest
from verification.aws_deployment import (
    AWSDeploymentExecutor,
    DeploymentError,
    DeploymentRequest,
)


class FakeAWSClient:
    def deploy(self, *, target, region, arguments):
        return {
            "success": True,
            "output": "deployment completed",
            "status_code": 200,
        }


def make_executor(client=None):
    return AWSDeploymentExecutor(
        account_id="904557616330",
        region="us-east-1",
        target="test-environment",
        client=client or FakeAWSClient(),
    )


@pytest.mark.parametrize(
    "field,value",
    [
        ("account_id", "999999999999"),
        ("region", "us-west-2"),
        ("target", "production"),
        ("operation", "DELETE"),
    ],
)
def test_agent_cannot_inject_authority_fields(field, value):
    executor = make_executor()

    request = DeploymentRequest(
        operation="DEPLOY",
        target="test-environment",
        arguments={field: value},
    )

    with pytest.raises(DeploymentError):
        executor.execute(request)


def test_agent_cannot_supply_credentials():
    executor = make_executor()

    request = DeploymentRequest(
        operation="DEPLOY",
        target="test-environment",
        arguments={
            "aws_access_key_id": "ATTACKER_KEY",
            "aws_secret_access_key": "ATTACKER_SECRET",
            "aws_session_token": "ATTACKER_TOKEN",
        },
    )

    result = executor.execute(request)

    assert result.success is True
    assert result.account_id == "904557616330"
    assert result.region == "us-east-1"
    assert result.target == "test-environment"


def test_agent_cannot_replace_deployment_operation():
    executor = make_executor()

    request = DeploymentRequest(
        operation="DELETE",
        target="test-environment",
        arguments={},
    )

    with pytest.raises(DeploymentError):
        executor.execute(request)


def test_forged_success_response_is_not_accepted_when_success_is_not_boolean():
    class ForgedClient:
        def deploy(self, *, target, region, arguments):
            return {
                "success": "true",
                "output": "deployment succeeded",
            }

    executor = make_executor(ForgedClient())

    result = executor.execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={},
        )
    )

    assert result.success is False
    assert result.error == "deployment response missing boolean success"


def test_executor_failure_cannot_become_success():
    class FailingClient:
        def deploy(self, *, target, region, arguments):
            return {
                "success": False,
                "error": "AWS authorization denied",
                "status_code": 403,
            }

    executor = make_executor(FailingClient())

    result = executor.execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={},
        )
    )

    assert result.success is False
    assert result.error == "AWS authorization denied"
    assert result.status_code == 403


def test_deployment_is_denied_before_dfa_build_state():
    executor = make_executor()

    runtime = AgentToolRuntime(
        {
            "deploy": lambda arguments: executor.execute(
                DeploymentRequest(
                    operation="DEPLOY",
                    target="test-environment",
                    arguments=arguments,
                )
            )
        }
    )

    with pytest.raises(AgentToolError):
        runtime.execute_tool(
            ToolRequest("deploy", {"artifact": "build-001"})
        )


def test_deployment_is_denied_after_complete():
    executor = make_executor()

    runtime = AgentToolRuntime(
        {
            "deploy": lambda arguments: executor.execute(
                DeploymentRequest(
                    operation="DEPLOY",
                    target="test-environment",
                    arguments=arguments,
                )
            )
        }
    )

    runtime.start()
    runtime.abort()

    with pytest.raises(AgentToolError):
        runtime.execute_tool(
            ToolRequest("deploy", {"artifact": "build-001"})
        )


def test_deployment_target_is_fixed_even_when_client_receives_arguments():
    observed = {}

    class ObservingClient:
        def deploy(self, *, target, region, arguments):
            observed["target"] = target
            observed["region"] = region
            observed["arguments"] = arguments
            return {"success": True}

    executor = make_executor(ObservingClient())

    executor.execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={"artifact": "build-001"},
        )
    )

    assert observed["target"] == "test-environment"
    assert observed["region"] == "us-east-1"
    assert observed["arguments"] == {"artifact": "build-001"}


def test_arbitrary_shell_command_is_not_available():
    executor = make_executor()

    assert not hasattr(executor.client, "shell")
    assert not hasattr(executor, "run_shell")
    assert not hasattr(executor, "execute_command")
