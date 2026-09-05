import pytest

from verification.aws_deployment import (
    AWSDeploymentExecutor,
    DeploymentError,
    DeploymentRequest,
)


class FakeAWSClient:
    def deploy(self, *, target, region, arguments):
        return {
            "success": True,
            "output": f"deployed {target} in {region}",
            "status_code": 200,
        }


def make_executor(client=None):
    return AWSDeploymentExecutor(
        account_id="904557616330",
        region="us-east-1",
        target="test-environment",
        client=client or FakeAWSClient(),
    )


def test_authorized_deployment_uses_verifier_configuration():
    executor = make_executor()

    result = executor.execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={"artifact": "build-001"},
        )
    )

    assert result.success is True
    assert result.operation == "DEPLOY"
    assert result.target == "test-environment"
    assert result.account_id == "904557616330"
    assert result.region == "us-east-1"
    assert result.status_code == 200


def test_wrong_target_is_rejected():
    executor = make_executor()

    with pytest.raises(DeploymentError):
        executor.execute(
            DeploymentRequest(
                operation="DEPLOY",
                target="production",
                arguments={},
            )
        )


def test_unauthorized_operation_is_rejected():
    executor = make_executor()

    with pytest.raises(DeploymentError):
        executor.execute(
            DeploymentRequest(
                operation="DELETE",
                target="test-environment",
                arguments={},
            )
        )


@pytest.mark.parametrize("field", ["account_id", "region", "target", "operation"])
def test_agent_cannot_override_verifier_configuration(field):
    executor = make_executor()

    with pytest.raises(DeploymentError):
        executor.execute(
            DeploymentRequest(
                operation="DEPLOY",
                target="test-environment",
                arguments={field: "attacker-controlled-value"},
            )
        )


def test_non_request_object_is_rejected():
    executor = make_executor()

    with pytest.raises(DeploymentError):
        executor.execute("DEPLOY")


def test_missing_deploy_operation_is_explicit_failure():
    class InvalidClient:
        pass

    executor = make_executor(InvalidClient())

    with pytest.raises(DeploymentError):
        executor.execute(
            DeploymentRequest(
                operation="DEPLOY",
                target="test-environment",
                arguments={},
            )
        )


def test_aws_exception_becomes_structured_failure():
    class FailingClient:
        def deploy(self, *, target, region, arguments):
            raise RuntimeError("AWS deployment failed")

    executor = make_executor(FailingClient())

    result = executor.execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={},
        )
    )

    assert result.success is False
    assert result.error == "AWS deployment failed"
    assert result.account_id == "904557616330"
    assert result.region == "us-east-1"


def test_malformed_response_becomes_structured_failure():
    class MalformedClient:
        def deploy(self, *, target, region, arguments):
            return "deployment succeeded"

    executor = make_executor(MalformedClient())

    result = executor.execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={},
        )
    )

    assert result.success is False
    assert result.error == "malformed deployment response"


def test_missing_success_field_becomes_structured_failure():
    class IncompleteClient:
        def deploy(self, *, target, region, arguments):
            return {"output": "something happened"}

    executor = make_executor(IncompleteClient())

    result = executor.execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={},
        )
    )

    assert result.success is False
    assert result.error == "deployment response missing boolean success"
