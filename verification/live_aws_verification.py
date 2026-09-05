"""Opt-in live AWS deployment and independent observation for v3.4."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from verification.aws_deployment import DeploymentRequest, DeploymentResult


class LiveAWSVerificationError(RuntimeError):
    """Raised when live AWS verification cannot safely proceed."""


@dataclass(frozen=True)
class ObservationResult:
    success: bool
    target: str
    account_id: str
    region: str
    observed_state: Mapping[str, Any]
    error: str = ""


@dataclass(frozen=True)
class DeploymentVerificationResult:
    deployment: DeploymentResult
    observation: ObservationResult
    verified: bool
    expected_state: Mapping[str, Any]


class S3LiveDeploymentBoundary:
    """Verifier-owned live deployment boundary using one configured S3 object.

    This is intentionally narrow: the only deployment operation is PUT_OBJECT
    against one exact bucket/key. The agent cannot select the bucket, key,
    account, or region.
    """

    OPERATION = "PUT_OBJECT"

    def __init__(self, *, account_id: str, region: str, bucket: str, key: str, client: Any) -> None:
        for name, value in (("account_id", account_id), ("region", region), ("bucket", bucket), ("key", key)):
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} must be non-empty")
        self.account_id = account_id
        self.region = region
        self.bucket = bucket
        self.key = key
        self.client = client

    @property
    def target(self) -> str:
        return f"s3://{self.bucket}/{self.key}"

    def deploy(self, request: DeploymentRequest) -> DeploymentResult:
        if request.operation != self.OPERATION:
            raise LiveAWSVerificationError("unauthorized live AWS operation")
        if request.target != self.target:
            raise LiveAWSVerificationError("live AWS target does not match verifier configuration")
        forbidden = {"account_id", "region", "bucket", "key", "target", "operation", "credentials"}
        if forbidden.intersection(request.arguments):
            raise LiveAWSVerificationError("verifier-controlled AWS fields cannot be overridden")

        body = request.arguments.get("body", "agent-verification-v3.4")
        if not isinstance(body, str):
            raise LiveAWSVerificationError("deployment body must be a string")

        try:
            self.client.put_object(Bucket=self.bucket, Key=self.key, Body=body.encode("utf-8"))
        except Exception as exc:
            return DeploymentResult(
                operation=request.operation,
                success=False,
                target=self.target,
                account_id=self.account_id,
                region=self.region,
                error=str(exc),
            )

        return DeploymentResult(
            operation=request.operation,
            success=True,
            target=self.target,
            account_id=self.account_id,
            region=self.region,
            output="S3 object deployment acknowledged",
            status_code=200,
        )

    def observe(self) -> ObservationResult:
        try:
            identity = self.client.get_caller_identity() if hasattr(self.client, "get_caller_identity") else None
            if identity is not None and str(identity.get("Account", "")) != self.account_id:
                return ObservationResult(False, self.target, str(identity.get("Account", "")), self.region, {}, "AWS account identity mismatch")

            response = self.client.head_object(Bucket=self.bucket, Key=self.key)
            return ObservationResult(
                success=True,
                target=self.target,
                account_id=self.account_id,
                region=self.region,
                observed_state={"exists": True, "content_length": response.get("ContentLength")},
            )
        except Exception as exc:
            return ObservationResult(
                success=False,
                target=self.target,
                account_id=self.account_id,
                region=self.region,
                observed_state={"exists": False},
                error=str(exc),
            )

    def verify(self, deployment: DeploymentResult, expected_state: Mapping[str, Any]) -> DeploymentVerificationResult:
        if not deployment.success:
            observation = ObservationResult(False, self.target, self.account_id, self.region, {}, "deployment did not succeed")
            return DeploymentVerificationResult(deployment, observation, False, dict(expected_state))

        observation = self.observe()
        verified = observation.success and all(observation.observed_state.get(k) == v for k, v in expected_state.items())
        return DeploymentVerificationResult(deployment, observation, verified, dict(expected_state))


def build_boto3_s3_boundary(*, account_id: str, region: str, bucket: str, key: str) -> S3LiveDeploymentBoundary:
    """Create the opt-in real AWS boundary using ambient verifier credentials."""
    try:
        import boto3
    except ImportError as exc:
        raise LiveAWSVerificationError("Install boto3 for live AWS tests: python -m pip install boto3") from exc

    session = boto3.Session(region_name=region)
    sts = session.client("sts")
    observed_account = str(sts.get_caller_identity()["Account"])
    if observed_account != account_id:
        raise LiveAWSVerificationError("configured AWS account does not match active credentials")
    return S3LiveDeploymentBoundary(
        account_id=account_id,
        region=region,
        bucket=bucket,
        key=key,
        client=_S3ClientWithIdentity(session.client("s3"), sts),
    )


class _S3ClientWithIdentity:
    def __init__(self, s3: Any, sts: Any) -> None:
        self._s3 = s3
        self._sts = sts

    def put_object(self, **kwargs: Any) -> Any:
        return self._s3.put_object(**kwargs)

    def head_object(self, **kwargs: Any) -> Any:
        return self._s3.head_object(**kwargs)

    def get_caller_identity(self) -> Mapping[str, Any]:
        return self._sts.get_caller_identity()
