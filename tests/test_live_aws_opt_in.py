import os
import uuid

import pytest

from verification.aws_deployment import DeploymentRequest
from verification.live_aws_verification import build_boto3_s3_boundary


pytestmark = pytest.mark.skipif(
    os.getenv("AGENT_VERIFICATION_LIVE_AWS") != "1",
    reason="live AWS integration is opt-in",
)


def test_real_s3_deployment_and_independent_observation():
    account_id = os.environ["AGENT_VERIFICATION_AWS_ACCOUNT_ID"]
    region = os.environ.get("AGENT_VERIFICATION_AWS_REGION", "us-east-1")
    bucket = os.environ["AGENT_VERIFICATION_S3_BUCKET"]
    key = f"agent-verification-v3.4/{uuid.uuid4().hex}.txt"

    boundary = build_boto3_s3_boundary(
        account_id=account_id,
        region=region,
        bucket=bucket,
        key=key,
    )

    try:
        deployment = boundary.deploy(
            DeploymentRequest(
                operation="PUT_OBJECT",
                target=boundary.target,
                arguments={"body": "agent-verification-v3.4-live-test"},
            )
        )
        assert deployment.success is True

        verification = boundary.verify(deployment, {"exists": True})
        assert verification.observation.success is True
        assert verification.verified is True
    finally:
        boundary.client._s3.delete_object(Bucket=bucket, Key=key)
