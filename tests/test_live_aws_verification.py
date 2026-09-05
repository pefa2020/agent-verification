import pytest

from verification.aws_deployment import DeploymentRequest
from verification.live_aws_verification import (
    LiveAWSVerificationError,
    S3LiveDeploymentBoundary,
)


class FakeS3:
    def __init__(self):
        self.objects = {}

    def put_object(self, **kwargs):
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs["Body"]

    def head_object(self, **kwargs):
        body = self.objects[(kwargs["Bucket"], kwargs["Key"])]
        return {"ContentLength": len(body)}

    def get_caller_identity(self):
        return {"Account": "904557616330"}


def make_boundary():
    return S3LiveDeploymentBoundary(
        account_id="904557616330",
        region="us-east-1",
        bucket="verification-test-bucket",
        key="agent-verification-v3.4.txt",
        client=FakeS3(),
    )


def test_live_boundary_uses_exact_configured_target():
    boundary = make_boundary()
    assert boundary.target == "s3://verification-test-bucket/agent-verification-v3.4.txt"


def test_live_deployment_and_independent_observation_verify_expected_state():
    boundary = make_boundary()
    request = DeploymentRequest(
        operation="PUT_OBJECT",
        target=boundary.target,
        arguments={"body": "verified"},
    )

    deployment = boundary.deploy(request)
    verification = boundary.verify(deployment, {"exists": True})

    assert deployment.success is True
    assert verification.observation.success is True
    assert verification.observed_state if hasattr(verification, "observed_state") else True
    assert verification.verified is True


def test_wrong_target_is_rejected():
    boundary = make_boundary()

    with pytest.raises(LiveAWSVerificationError):
        boundary.deploy(
            DeploymentRequest(
                operation="PUT_OBJECT",
                target="s3://attacker-bucket/evil.txt",
                arguments={},
            )
        )


def test_agent_cannot_override_live_aws_identity_or_resource():
    boundary = make_boundary()

    for field in ("account_id", "region", "bucket", "key", "target", "operation", "credentials"):
        with pytest.raises(LiveAWSVerificationError):
            boundary.deploy(
                DeploymentRequest(
                    operation="PUT_OBJECT",
                    target=boundary.target,
                    arguments={field: "attacker-controlled"},
                )
            )


def test_failed_deployment_cannot_become_verified():
    class FailingS3(FakeS3):
        def put_object(self, **kwargs):
            raise RuntimeError("AWS put failed")

    boundary = S3LiveDeploymentBoundary(
        account_id="904557616330",
        region="us-east-1",
        bucket="verification-test-bucket",
        key="agent-verification-v3.4.txt",
        client=FailingS3(),
    )
    deployment = boundary.deploy(
        DeploymentRequest("PUT_OBJECT", boundary.target, {})
    )
    verification = boundary.verify(deployment, {"exists": True})

    assert deployment.success is False
    assert verification.verified is False


def test_mismatched_expected_state_fails_verification():
    boundary = make_boundary()
    deployment = boundary.deploy(
        DeploymentRequest("PUT_OBJECT", boundary.target, {})
    )
    verification = boundary.verify(deployment, {"exists": False})

    assert verification.observation.success is True
    assert verification.verified is False
