"""Verifier-owned, bounded AWS deployment executor for v3.3."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class DeploymentError(RuntimeError):
    """Raised when a deployment request violates the configured boundary."""


@dataclass(frozen=True)
class DeploymentRequest:
    operation: str
    target: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class DeploymentResult:
    operation: str
    success: bool
    target: str
    account_id: str
    region: str
    output: str = ""
    error: str = ""
    status_code: int | None = None


class AWSDeploymentExecutor:
    """Execute only verifier-configured deployment operations.

    The concrete AWS client is injected by the verifier/application.
    Agent-supplied arguments cannot replace the configured account, region,
    target, or operation.
    """

    OPERATIONS = frozenset({"DEPLOY"})

    def __init__(
        self,
        *,
        account_id: str,
        region: str,
        target: str,
        client: Any,
        operation_handler: Any | None = None,
    ) -> None:
        if not account_id.strip():
            raise ValueError("account_id must be non-empty")
        if not region.strip():
            raise ValueError("region must be non-empty")
        if not target.strip():
            raise ValueError("target must be non-empty")

        self.account_id = account_id
        self.region = region
        self.target = target
        self.client = client
        self._operation_handler = operation_handler

    def execute(self, request: DeploymentRequest) -> DeploymentResult:
        if not isinstance(request, DeploymentRequest):
            raise DeploymentError("invalid deployment request")

        if request.operation not in self.OPERATIONS:
            raise DeploymentError(
                f"unauthorized deployment operation: {request.operation}"
            )

        if request.target != self.target:
            raise DeploymentError("deployment target does not match verifier configuration")

        if "account_id" in request.arguments:
            raise DeploymentError("account_id is verifier-controlled")

        if "region" in request.arguments:
            raise DeploymentError("region is verifier-controlled")

        if "target" in request.arguments:
            raise DeploymentError("target is verifier-controlled")

        if "operation" in request.arguments:
            raise DeploymentError("operation is verifier-controlled")

        try:
            if self._operation_handler is not None:
                raw = self._operation_handler(
                    client=self.client,
                    target=self.target,
                    arguments=dict(request.arguments),
                )
            else:
                deploy = getattr(self.client, "deploy", None)
                if deploy is None or not callable(deploy):
                    raise DeploymentError(
                        "configured AWS client does not expose the approved deploy operation"
                    )
                raw = deploy(
                    target=self.target,
                    region=self.region,
                    arguments=dict(request.arguments),
                )
        except DeploymentError:
            raise
        except Exception as exc:
            return DeploymentResult(
                operation=request.operation,
                success=False,
                target=self.target,
                account_id=self.account_id,
                region=self.region,
                error=str(exc),
            )

        if not isinstance(raw, Mapping):
            return DeploymentResult(
                operation=request.operation,
                success=False,
                target=self.target,
                account_id=self.account_id,
                region=self.region,
                error="malformed deployment response",
            )

        success = raw.get("success")
        if not isinstance(success, bool):
            return DeploymentResult(
                operation=request.operation,
                success=False,
                target=self.target,
                account_id=self.account_id,
                region=self.region,
                error="deployment response missing boolean success",
            )

        return DeploymentResult(
            operation=request.operation,
            success=success,
            target=self.target,
            account_id=self.account_id,
            region=self.region,
            output=str(raw.get("output", "")),
            error=str(raw.get("error", "")),
            status_code=raw.get("status_code"),
        )
