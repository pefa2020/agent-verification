"""Deterministic v3.3 AWS deployment boundary invariant checks."""

from __future__ import annotations

from verification.agent_tool_runtime import AgentToolError, AgentToolRuntime, ToolRequest
from verification.aws_deployment import (
    AWSDeploymentExecutor,
    DeploymentError,
    DeploymentRequest,
)
from verification.aws_deployment_evidence import deployment_evidence_payload
from verification.evidence_integrity import EvidenceLedger, IntegrityError


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


def invariant_d1_verifier_selected_target() -> bool:
    executor = make_executor()

    try:
        executor.execute(
            DeploymentRequest(
                operation="DEPLOY",
                target="production",
                arguments={},
            )
        )
    except DeploymentError:
        return True

    return False


def invariant_d2_verifier_selected_operation() -> bool:
    executor = make_executor()

    try:
        executor.execute(
            DeploymentRequest(
                operation="DELETE",
                target="test-environment",
                arguments={},
            )
        )
    except DeploymentError:
        return True

    return False


def invariant_d3_state_gated_deployment() -> bool:
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

    try:
        runtime.execute_tool(ToolRequest("deploy", {}))
    except AgentToolError:
        return True

    return False


def invariant_d4_executor_authority() -> bool:
    class FakeFailureClient:
        def deploy(self, *, target, region, arguments):
            return {
                "success": False,
                "error": "deployment failed",
                "status_code": 500,
            }

    result = make_executor(FakeFailureClient()).execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={},
        )
    )

    return result.success is False


def invariant_d5_failure_containment() -> bool:
    class ExplodingClient:
        def deploy(self, *, target, region, arguments):
            raise RuntimeError("AWS failure")

    result = make_executor(ExplodingClient()).execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={},
        )
    )

    return result.success is False and result.error == "AWS failure"


def invariant_d6_evidence_validation() -> bool:
    runtime = AgentToolRuntime({})
    runtime.start()
    runtime.mark_build_ready()

    result = make_executor().execute(
        DeploymentRequest(
            operation="DEPLOY",
            target="test-environment",
            arguments={},
        )
    )

    payload = deployment_evidence_payload(
        result,
        run_id="d6-run",
        commit="abc123",
    )

    try:
        runtime.submit_evidence(payload)
    except ValueError:
        return True

    return False


def invariant_d7_evidence_integrity() -> bool:
    ledger = EvidenceLedger()

    payload = deployment_evidence_payload(
        make_executor().execute(
            DeploymentRequest(
                operation="DEPLOY",
                target="test-environment",
                arguments={},
            )
        ),
        run_id="d7-run",
        commit="abc123",
    )

    ledger.append(payload)

    try:
        ledger.append(payload)
    except IntegrityError:
        return ledger.verify()

    return False


def invariant_d8_credential_boundary() -> bool:
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

    return (
        result.success is True
        and result.account_id == "904557616330"
        and result.region == "us-east-1"
        and result.target == "test-environment"
    )


def invariant_d9_no_unrestricted_aws_interface() -> bool:
    executor = make_executor()

    return (
        not hasattr(executor, "run_shell")
        and not hasattr(executor, "execute_command")
        and not hasattr(executor.client, "shell")
    )


def invariant_d10_reproducibility() -> bool:
    def run_once():
        executor = make_executor()
        result = executor.execute(
            DeploymentRequest(
                operation="DEPLOY",
                target="test-environment",
                arguments={"artifact": "build-001"},
            )
        )
        return (
            result.operation,
            result.success,
            result.target,
            result.account_id,
            result.region,
            result.output,
            result.error,
            result.status_code,
        )

    return run_once() == run_once()


INVARIANTS = {
    "D1": invariant_d1_verifier_selected_target,
    "D2": invariant_d2_verifier_selected_operation,
    "D3": invariant_d3_state_gated_deployment,
    "D4": invariant_d4_executor_authority,
    "D5": invariant_d5_failure_containment,
    "D6": invariant_d6_evidence_validation,
    "D7": invariant_d7_evidence_integrity,
    "D8": invariant_d8_credential_boundary,
    "D9": invariant_d9_no_unrestricted_aws_interface,
    "D10": invariant_d10_reproducibility,
}


def run_invariants() -> dict[str, bool]:
    return {name: check() for name, check in INVARIANTS.items()}
