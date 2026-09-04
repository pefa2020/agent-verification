import os

import pytest

from dfa.states import State
from verification.agent_tool_runtime import AgentToolRuntime
from verification.llm_agent_runtime import LLMIntegrationError, OpenAILLMAdapter


class FakeFunctionCall:
    type = "function_call"

    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class FakeResponse:
    output_text = "done"

    def __init__(self, output):
        self.output = output


class FakeResponses:
    def __init__(self, response):
        self.response = response
        self.kwargs = None

    def create(self, **kwargs):
        self.kwargs = kwargs
        return self.response


class FakeClient:
    def __init__(self, response):
        self.responses = FakeResponses(response)


def test_live_adapter_routes_model_tool_call_through_runtime(monkeypatch):
    response = FakeResponse([FakeFunctionCall("echo", '{"value":"hello"}')])
    client = FakeClient(response)

    import openai

    monkeypatch.setattr(openai, "OpenAI", lambda: client)
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    output, transcript = OpenAILLMAdapter(runtime, model="test-model").run("say hello")

    assert output == "done"
    assert transcript == [
        {"tool": "echo", "allowed": True, "success": True, "output": "hello", "error": ""}
    ]
    assert runtime.state is State.BUILD
    assert client.responses.kwargs["parallel_tool_calls"] is False


def test_live_adapter_records_runtime_denial(monkeypatch):
    response = FakeResponse([FakeFunctionCall("unknown", "{}")])
    client = FakeClient(response)

    import openai

    monkeypatch.setattr(openai, "OpenAI", lambda: client)
    runtime = AgentToolRuntime({"echo": lambda args: args})
    adapter = OpenAILLMAdapter(runtime, model="test-model")
    output, transcript = adapter.run("use an unavailable tool")

    assert output == "done"
    assert transcript[0]["allowed"] is False
    assert "Unknown tool" in transcript[0]["error"]
    assert runtime.state is State.BUILD


def test_live_adapter_requires_optional_openai_dependency(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("blocked for test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    runtime = AgentToolRuntime({"echo": lambda args: args})
    with pytest.raises(LLMIntegrationError, match="optional OpenAI dependency"):
        OpenAILLMAdapter(runtime).run("hello")


@pytest.mark.skipif(not os.getenv("OPENAI_API_KEY"), reason="live LLM test requires OPENAI_API_KEY")
def test_live_openai_model_can_request_verifier_owned_tool():
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    output, transcript = OpenAILLMAdapter(runtime).run(
        "Use the echo tool with value 'live-llm-verification', then report the tool result."
    )

    assert output or transcript
    assert any(item.get("tool") == "echo" for item in transcript)
    assert all(item.get("allowed") is True for item in transcript)
    assert runtime.state is State.BUILD
