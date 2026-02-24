"""Tests for shared Pydantic schemas."""
import pytest
from homelab_schemas import (
    ChatRequest,
    ChatResponse,
    LLMRequest,
    LLMResponse,
    ToolDefinition,
    ToolParameter,
)


class TestChatRequest:
    def test_message_only(self):
        req = ChatRequest(message="hello")
        assert req.message == "hello"
        assert req.conversation_id is None

    def test_with_conversation_id(self):
        req = ChatRequest(message="hello", conversation_id="abc-123")
        assert req.conversation_id == "abc-123"

    def test_empty_message_is_allowed(self):
        req = ChatRequest(message="")
        assert req.message == ""


class TestChatResponse:
    def test_tool_calls_default_to_empty_list(self):
        resp = ChatResponse(message="hi", conversation_id="abc")
        assert resp.tool_calls_made == []

    def test_tool_calls_populated(self):
        resp = ChatResponse(
            message="hi",
            conversation_id="abc",
            tool_calls_made=["get_system_resources", "list_containers"],
        )
        assert len(resp.tool_calls_made) == 2
        assert "get_system_resources" in resp.tool_calls_made


class TestToolDefinition:
    def test_to_openai_function_no_parameters(self):
        tool = ToolDefinition(name="get_system_resources", description="Get system resources")
        result = tool.to_openai_function()
        assert result["type"] == "function"
        assert result["function"]["name"] == "get_system_resources"
        assert result["function"]["description"] == "Get system resources"
        assert result["function"]["parameters"]["properties"] == {}
        assert result["function"]["parameters"]["required"] == []

    def test_to_openai_function_required_parameter(self):
        tool = ToolDefinition(
            name="get_logs",
            description="Get logs",
            parameters=[
                ToolParameter(
                    name="service", type="string", description="Service name", required=True
                )
            ],
        )
        result = tool.to_openai_function()
        props = result["function"]["parameters"]["properties"]
        assert "service" in props
        assert props["service"]["type"] == "string"
        assert props["service"]["description"] == "Service name"
        assert "service" in result["function"]["parameters"]["required"]

    def test_to_openai_function_optional_parameter_excluded_from_required(self):
        tool = ToolDefinition(
            name="search",
            description="Search logs",
            parameters=[
                ToolParameter(
                    name="filter", type="string", description="Filter string", required=False
                )
            ],
        )
        result = tool.to_openai_function()
        assert "filter" in result["function"]["parameters"]["properties"]
        assert "filter" not in result["function"]["parameters"]["required"]

    def test_to_openai_function_parameter_with_enum(self):
        tool = ToolDefinition(
            name="set_log_level",
            description="Set log level",
            parameters=[
                ToolParameter(
                    name="level",
                    type="string",
                    description="Log level",
                    required=True,
                    enum=["debug", "info", "warning", "error"],
                )
            ],
        )
        result = tool.to_openai_function()
        props = result["function"]["parameters"]["properties"]
        assert props["level"]["enum"] == ["debug", "info", "warning", "error"]

    def test_to_openai_function_multiple_parameters(self):
        tool = ToolDefinition(
            name="multi_param",
            description="Test tool",
            parameters=[
                ToolParameter(name="a", type="string", description="A", required=True),
                ToolParameter(name="b", type="integer", description="B", required=False),
            ],
        )
        result = tool.to_openai_function()
        assert "a" in result["function"]["parameters"]["required"]
        assert "b" not in result["function"]["parameters"]["required"]
        assert "a" in result["function"]["parameters"]["properties"]
        assert "b" in result["function"]["parameters"]["properties"]


class TestLLMResponse:
    def test_content_only_response(self):
        resp = LLMResponse(content="Hello!", finish_reason="stop")
        assert resp.content == "Hello!"
        assert resp.tool_calls == []
        assert resp.finish_reason == "stop"

    def test_tool_calls_response(self):
        resp = LLMResponse(
            content=None,
            tool_calls=[{"id": "tc_1", "name": "get_system_resources", "arguments": {}}],
            finish_reason="tool_calls",
        )
        assert resp.content is None
        assert len(resp.tool_calls) == 1
        assert resp.tool_calls[0]["name"] == "get_system_resources"

    def test_finish_reason_is_required(self):
        with pytest.raises(Exception):
            LLMResponse(content="hi")  # missing finish_reason


class TestLLMRequest:
    def test_minimal_request(self):
        req = LLMRequest(messages=[{"role": "user", "content": "hi"}])
        assert len(req.messages) == 1
        assert req.tools == []
        assert req.system_prompt is None

    def test_with_system_prompt(self):
        req = LLMRequest(
            messages=[{"role": "user", "content": "hi"}],
            system_prompt="You are a helpful assistant.",
        )
        assert req.system_prompt == "You are a helpful assistant."
