"""Optional live LLM adapter that routes model tool calls through the verifier."""

from __future__ import annotations

import json
import os
from typing import Any

from verification.agent_tool_runtime import AgentToolError, AgentToolRuntime, ToolRequest


class LLMIntegrationError(RuntimeError):
    """Raised when live LLM integration cannot complete safely."""


class OpenAILLMAdapter:
    """OpenAI Responses API adapter with a verifier-owned tool boundary."""

    def __init__(self, runtime: AgentToolRuntime, client: Any = None, model: str | None = None):
        self.runtime = runtime
        self.model = model or os.getenv("AGENT_VERIFICATION_MODEL", "gpt-5")
        self._client = client

    def _client_or_default(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise LLMIntegrationError(
                "Install the optional OpenAI dependency with: python -m pip install openai"
            ) from exc
        return OpenAI()

    def _tool_schema(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "name": name,
                "description": f"Verifier-controlled tool named {name}",
                "parameters": {
                    "type": "object",
                    "properties": {"value": {"type": "string"}},
                    "required": ["value"],
                    "additionalProperties": False,
                },
                "strict": True,
            }
            for name in self.runtime.tools
        ]

    def run(self, prompt: str, *, max_turns: int = 4) -> tuple[str, list[dict[str, Any]]]:
        if not isinstance(prompt, str) or not prompt.strip():
            raise LLMIntegrationError("prompt must be a non-empty string")
        if max_turns < 1:
            raise LLMIntegrationError("max_turns must be at least 1")

        client = self._client_or_default()
        self.runtime.start()
        tools = self._tool_schema()
        response = client.responses.create(
            model=self.model,
            instructions=(
                "You are an agent operating inside a verification harness. "
                "Request verifier-owned tools when useful. Never claim a tool "
                "executed unless the verifier runtime returns a result."
            ),
            input=prompt,
            tools=tools,
            parallel_tool_calls=False,
        )

        transcript: list[dict[str, Any]] = []
        for _ in range(max_turns):
            calls = [item for item in response.output if getattr(item, "type", None) == "function_call"]
            if not calls:
                return getattr(response, "output_text", ""), transcript

            tool_outputs: list[dict[str, Any]] = []
            for item in calls:
                name = item.name
                try:
                    arguments = json.loads(item.arguments or "{}")
                except json.JSONDecodeError as exc:
                    raise LLMIntegrationError(
                        f"Model emitted invalid JSON arguments for {name}"
                    ) from exc
                if not isinstance(arguments, dict):
                    raise LLMIntegrationError(f"Model arguments for {name} must be a JSON object")

                request = ToolRequest(name=name, arguments=arguments)
                try:
                    result = self.runtime.execute_tool(request)
                    entry = {
                        "tool": name,
                        "allowed": True,
                        "success": result.success,
                        "output": result.output,
                        "error": result.error,
                    }
                    tool_output = {
                        "success": result.success,
                        "output": result.output,
                        "error": result.error,
                    }
                except AgentToolError as exc:
                    entry = {"tool": name, "allowed": False, "error": str(exc)}
                    tool_output = {"success": False, "output": None, "error": str(exc)}

                transcript.append(entry)
                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(tool_output, default=str),
                    }
                )

            response = client.responses.create(
                model=self.model,
                previous_response_id=response.id,
                input=tool_outputs,
                tools=tools,
                parallel_tool_calls=False,
            )

        raise LLMIntegrationError("LLM exceeded maximum tool-use turns")
