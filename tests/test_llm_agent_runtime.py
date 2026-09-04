import os

import pytest

from dfa.states import State
from verification.agent_tool_runtime import AgentToolRuntime
from verification.llm_agent_runtime import LLMIntegrationError, OpenAILLMAdapter


class FakeFunctionCall:
    type = "function_call"

    def __init__(self, name, arguments, call_id="call_1"):
        self.name = name
        self.arguments = arguments
        self.call_id = call_id


class FakeResponse:
    output_text = "done"

    def __init__(self, output, response_id="resp_1"):
        self.output = output
        self.id = response_id


class FakeResponses:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return next(self.responses)


class FakeClient:
    def __init__(self, responses):
        self.responses = FakeResponses(responses)


def test_llm_adapter_routes_model_tool_call_through_runtime():
    client = FakeClient(
        [
            FakeResponse([FakeFunctionCall("echo", '{"value":"hello"}')]),
            FakeResponse([], response_id="resp_2"),
        ]
    )
    runtime = AgentToolRuntime({"echo": lambda args: args["value"]})
    output, transcript = OpenAILLMAdapter(runtime, client=client, model="test-model").run("say hello")

    assert output == "done"
    assert transcript == [
        {"tool": "echo", "allowed": True, "success": True, "output": "hello", "error": ""}
    ]
    assert runtime.state is State.BUILD
    assert client.responses.calls[0]["parallel_tool_calls"] is False
    assert client.responses.calls[1]["previous_response_id"] == "resp_1"
    assert client.responses.calls[1]["input"][0]["type"] == "function_call_output"
    assert client.responses.calls[1]["input"][0]["call_id"] == "call_1"


def test_llm_adapter_records_runtime_denial_and_returns_tool_error_to_model():
    client = FakeClient(
        [
            FakeResponse([FakeFunctionCall("unknown", "{}")]),
            FakeResponse([], response_id="resp_2"),
        ]
    )
    runtime = AgentToolRuntime({"echo": lambda args: args})
    output, transcript = OpenAILLMAdapter(runtime, client=client, model="test-model").run(
        "use an unavailable tool"
    )

    assert output == "done"
    assert transcript[0]["allowed"] is False
    assert "Unknown tool" in transcript[0]["error"]
    assert runtime.state is State.BUILD
    assert "Unknown tool" in client.responses.calls[1]["input"][0]["output"]


def test_llm_adapter_requires_optional_openai_dependency(monkeypatch):
    import builtins

    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("blocked for test")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked_import)
    runtime = AgentToolRuntime({"echo": lambda args: args})
    adapter = OpenAILLMAdapter(runtime, client=None)
    monkeypatch.setattr(adapter, "_client_or_default", lambda: (_ for _ in ()).throw(
        LLMIntegrationError("Install the optional OpenAI dependency")
    ))
    with pytest.raises(LLMIntegrationError, match="optional OpenAI dependency"):
        adapter.run("hello")


def test_llm_adapter_rejects_invalid_arguments_shape():
    client = FakeClient([FakeResponse([FakeFunctionCall("echo", "[]")])])
    runtime = AgentToolRuntime({"echo": lambda args: args})

    with pytest.raises(LLMIntegrationError, match="must be a JSON object"):
        OpenAILLMAdapter(runtime, client=client).run("hello")


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
