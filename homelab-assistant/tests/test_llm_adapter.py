"""Tests for the LLM Adapter service."""
import json

import pytest
from unittest.mock import AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_settings(mocker):
    mock = MagicMock()
    mock.llm_provider = "groq"
    mock.groq_api_key = "test-groq-key"
    mock.openai_api_key = "test-openai-key"
    mock.log_level = "WARNING"
    mocker.patch("llm_adapter.main.settings", mock)
    return mock


@pytest.fixture
async def adapter_client(mock_settings):
    from llm_adapter.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_health_no_provider(adapter_client, mocker):
    mocker.patch("llm_adapter.main.provider", None)
    mocker.patch("llm_adapter.main.provider_name", None)

    response = await adapter_client.get("/health")

    assert response.status_code == 200
    assert response.json()["provider"] == "none"


async def test_health_with_provider(adapter_client, mocker):
    mocker.patch("llm_adapter.main.provider", MagicMock())
    mocker.patch("llm_adapter.main.provider_name", "groq")

    response = await adapter_client.get("/health")

    assert response.status_code == 200
    assert response.json()["provider"] == "groq"


async def test_chat_without_provider_returns_503(adapter_client, mocker):
    mocker.patch("llm_adapter.main.provider", None)

    response = await adapter_client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "hello"}], "tools": []},
    )
    assert response.status_code == 503


async def test_chat_with_provider_returns_content(adapter_client, mocker):
    from homelab_schemas import LLMResponse

    mock_provider = AsyncMock()
    mock_provider.chat.return_value = LLMResponse(
        content="All systems are running normally.",
        tool_calls=[],
        finish_reason="stop",
    )
    mocker.patch("llm_adapter.main.provider", mock_provider)

    response = await adapter_client.post(
        "/chat",
        json={"messages": [{"role": "user", "content": "Is everything ok?"}], "tools": []},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["content"] == "All systems are running normally."
    assert data["finish_reason"] == "stop"


async def test_groq_provider_returns_text_response(mocker):
    from llm_adapter.providers.groq_provider import GroqProvider

    provider = GroqProvider(api_key="test-key")

    mock_message = MagicMock()
    mock_message.content = "CPU usage is 25%."
    mock_message.tool_calls = None
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_choice.finish_reason = "stop"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mocker.patch.object(
        provider.client.chat.completions,
        "create",
        new_callable=AsyncMock,
        return_value=mock_completion,
    )

    result = await provider.chat(
        messages=[{"role": "user", "content": "What is CPU usage?"}],
        tools=[],
    )

    assert result.content == "CPU usage is 25%."
    assert result.finish_reason == "stop"
    assert result.tool_calls == []


async def test_groq_provider_returns_tool_call(mocker):
    from llm_adapter.providers.groq_provider import GroqProvider

    provider = GroqProvider(api_key="test-key")

    mock_tool_call = MagicMock()
    mock_tool_call.id = "call_abc123"
    mock_tool_call.function.name = "get_system_resources"
    mock_tool_call.function.arguments = json.dumps({})

    mock_message = MagicMock()
    mock_message.content = None
    mock_message.tool_calls = [mock_tool_call]
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_choice.finish_reason = "tool_calls"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    mocker.patch.object(
        provider.client.chat.completions,
        "create",
        new_callable=AsyncMock,
        return_value=mock_completion,
    )

    result = await provider.chat(
        messages=[{"role": "user", "content": "Check system resources"}],
        tools=[],
    )

    assert result.content is None
    assert result.finish_reason == "tool_calls"
    assert len(result.tool_calls) == 1
    assert result.tool_calls[0]["name"] == "get_system_resources"
    assert result.tool_calls[0]["id"] == "call_abc123"
    assert result.tool_calls[0]["arguments"] == {}


async def test_groq_provider_prepends_system_prompt(mocker):
    from llm_adapter.providers.groq_provider import GroqProvider

    provider = GroqProvider(api_key="test-key")

    mock_message = MagicMock()
    mock_message.content = "I am a homelab assistant."
    mock_message.tool_calls = None
    mock_choice = MagicMock()
    mock_choice.message = mock_message
    mock_choice.finish_reason = "stop"
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]

    create_mock = mocker.patch.object(
        provider.client.chat.completions,
        "create",
        new_callable=AsyncMock,
        return_value=mock_completion,
    )

    await provider.chat(
        messages=[{"role": "user", "content": "Who are you?"}],
        tools=[],
        system_prompt="You are a homelab assistant.",
    )

    call_kwargs = create_mock.call_args[1]
    messages_sent = call_kwargs["messages"]
    assert messages_sent[0]["role"] == "system"
    assert messages_sent[0]["content"] == "You are a homelab assistant."
