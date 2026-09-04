"""Optional live LLM adapter that routes model tool calls through the verifier."""

from __future__ import annotations

import json
import os
from typing import Any

from verification.agent_tool_runtime import AgentToolError, AgentToolRuntime, ToolRequest


class LLMIntegrationError(RuntimeError):
    """Raised when live LLM integration cannot complete safely."""


class OpenAILLMAdapter:
    """Minimal OpenAI Responses API adapter with a verifier-owned tool boundary."""

    def __init__(self, runtime: AgentToolRuntime, model: str | None = None):
        self.runtime = runtime
        self.model = model or os.getenv("AGENT_VERIFICATION_MODEL", "gpt-5.6-luna")

    def run(self, prompt: str) -> tuple[str, list[dict[str, Any]]]:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMIntegrationError(
                "Install the optional OpenAI dependency with: python -m pip install openai"
            ) from exc

        client = OpenAI()
        self.runtime.start()
        tools = [
            {
                "type": "function",
                "name": name,
                "description": f"Verifier-controlled tool named {name}",
                "parameters": {
                    "type": "object",
                    "additionalProperties": True,
                },
                "strict": False,
            }
            for name in self.runtime.tools
        ]
        response = client.responses.create(
            model=self.model,
            instructions=(
                "You are an agent operating inside a verification harness. "
                "Request tools when useful. Never claim that a tool executed "
                "unless the verifier runtime returns a result."
            ),
            input=prompt,
            tools=tools,
            parallel_tool_calls=False,
        )

        transcript: list[dict[str, Any]] = []
        for item in response.output:
            if getattr(item, "type", None) != "function_call":
                continue
            name = item.name
            try:
                arguments = json.loads(item.arguments or "{}")
            except json.JSONDecodeError as exc:
                raise LLMIntegrationError(
                    f"Model emitted invalid JSON arguments for {name}"
                ) from exc
            request = ToolRequest(name=name, arguments=arguments)
            try:
                result = self.runtime.execute_tool(request)
            except AgentToolError as exc:
                transcript.append({"tool": name, "allowed": False, "error": str(exc)})
                continue
            transcript.append(
                {
                    "tool": name,
                    "allowed": True,
                    "success": result.success,
                    "output": result.output,
                    "error": result.error,
                }
            )
        return getattr(response, "output_text", ""), transcript
