"""End-to-end agentic harness combining the LLM, DFA, AWS boundary, and observation."""

from __future__ import annotations

from typing import Any

from verification.agent_tool_runtime import AgentToolRuntime
from verification.aws_deployment import DeploymentRequest
from verification.live_aws_verification import S3LiveDeploymentBoundary
from verification.llm_agent_runtime import OpenAILLMAdapter


class AgenticAWSVerifier:
    """Wire a real LLM tool loop to a verifier-owned live AWS boundary.

    The model sees only one verifier-owned tool. The tool performs deployment
    against the fixed target and independently observes the resulting object.
    """

    def __init__(self, boundary: S3LiveDeploymentBoundary, *, client: Any = None, model: str | None = None) -> None:
        self.boundary = boundary
        self.runtime = AgentToolRuntime({"deploy": self._deploy_tool})
        self.adapter = OpenAILLMAdapter(self.runtime, client=client, model=model)

    def _deploy_tool(self, arguments: dict[str, Any]) -> dict[str, Any]:
        body = arguments.get("value", "agent-verification-v3.4")
        if not isinstance(body, str):
            return {"success": False, "error": "deployment value must be a string"}

        deployment = self.boundary.deploy(
            DeploymentRequest(
                operation="PUT_OBJECT",
                target=self.boundary.target,
                arguments={"body": body},
            )
        )
        verification = self.boundary.verify(deployment, {"exists": True})
        return {
            "deployment_success": deployment.success,
            "deployment_error": deployment.error,
            "target": deployment.target,
            "account_id": deployment.account_id,
            "region": deployment.region,
            "observed_state": dict(verification.observation.observed_state),
            "observation_success": verification.observation.success,
            "verification_success": verification.verified,
            "observation_error": verification.observation.error,
        }

    def run(self, prompt: str, *, max_turns: int = 4):
        return self.adapter.run(prompt, max_turns=max_turns)
