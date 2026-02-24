"""Tests for the Orchestrator service."""
import pytest
from unittest.mock import AsyncMock, MagicMock

import httpx
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def mock_settings(mocker):
    mock = MagicMock()
    mock.llm_adapter_url = "http://test-llm:8002"
    mock.monitoring_url = "http://test-monitoring:8003"
    mock.audit_log_path = "/tmp/test-audit.jsonl"
    mocker.patch("orchestrator.main.settings", mock)
    return mock


@pytest.fixture
def mock_audit(mocker):
    return mocker.patch("orchestrator.main.write_audit_log", new_callable=AsyncMock)


@pytest.fixture
async def orchestrator_client(mock_settings, mock_audit):
    from orchestrator.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


def _mock_llm_http_client(mocker, responses: list):
    """Create a mock httpx.AsyncClient for the orchestrator's LLM calls."""
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.side_effect = responses
    mocker.patch("orchestrator.main.httpx.AsyncClient", return_value=mock_client)
    return mock_client


def _llm_response(content=None, tool_calls=None, finish_reason="stop"):
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "content": content,
        "tool_calls": tool_calls or [],
        "finish_reason": finish_reason,
    }
    return mock_resp


async def test_health_endpoint(orchestrator_client):
    response = await orchestrator_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "orchestrator"


async def test_chat_direct_llm_response(orchestrator_client, mock_audit, mocker):
    _mock_llm_http_client(mocker, [_llm_response(content="CPU usage is 25%")])

    response = await orchestrator_client.post(
        "/chat", json={"message": "What is CPU usage?"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "CPU usage is 25%"
    assert data["tool_calls_made"] == []
    assert "conversation_id" in data
    mock_audit.assert_called_once()


async def test_chat_with_tool_call(orchestrator_client, mock_audit, mocker):
    mocker.patch(
        "orchestrator.main.execute_tool",
        new_callable=AsyncMock,
        return_value={"cpu_percent": 25.0, "memory_percent": 50.0},
    )
    _mock_llm_http_client(
        mocker,
        [
            _llm_response(
                tool_calls=[{"id": "tc_1", "name": "get_system_resources", "arguments": {}}],
                finish_reason="tool_calls",
            ),
            _llm_response(content="CPU is at 25%, memory at 50%."),
        ],
    )

    response = await orchestrator_client.post("/chat", json={"message": "Check CPU"})

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "CPU is at 25%, memory at 50%."
    assert "get_system_resources" in data["tool_calls_made"]


async def test_chat_assigns_conversation_id_when_not_provided(
    orchestrator_client, mocker
):
    _mock_llm_http_client(mocker, [_llm_response(content="Hello")])

    response = await orchestrator_client.post("/chat", json={"message": "hi"})

    assert response.status_code == 200
    assert response.json()["conversation_id"] != ""


async def test_chat_preserves_provided_conversation_id(orchestrator_client, mocker):
    _mock_llm_http_client(mocker, [_llm_response(content="Hello")])

    response = await orchestrator_client.post(
        "/chat",
        json={"message": "hi", "conversation_id": "my-conv-123"},
    )

    assert response.json()["conversation_id"] == "my-conv-123"


async def test_chat_llm_adapter_unavailable_returns_502(orchestrator_client, mocker):
    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.post.side_effect = httpx.HTTPError("connection refused")
    mocker.patch("orchestrator.main.httpx.AsyncClient", return_value=mock_client)

    response = await orchestrator_client.post("/chat", json={"message": "hello"})
    assert response.status_code == 502


async def test_execute_tool_get_system_resources(mocker):
    from orchestrator.tools import execute_tool
    from homelab_common.config import Settings

    resource_data = {"cpu_percent": 30.0, "memory_total_gb": 16.0}
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = resource_data

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get.return_value = mock_resp
    mocker.patch("orchestrator.tools.httpx.AsyncClient", return_value=mock_client)

    result = await execute_tool("get_system_resources", {}, Settings())

    assert result == resource_data
    call_url = mock_client.get.call_args[0][0]
    assert "/system/resources" in call_url


async def test_execute_tool_list_containers(mocker):
    from orchestrator.tools import execute_tool
    from homelab_common.config import Settings

    containers = [{"id": "abc", "name": "gateway", "status": "running"}]
    mock_resp = MagicMock()
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = containers

    mock_client = AsyncMock()
    mock_client.__aenter__.return_value = mock_client
    mock_client.__aexit__.return_value = None
    mock_client.get.return_value = mock_resp
    mocker.patch("orchestrator.tools.httpx.AsyncClient", return_value=mock_client)

    result = await execute_tool("list_containers", {}, Settings())

    assert result == containers
    call_url = mock_client.get.call_args[0][0]
    assert "/containers" in call_url


async def test_execute_tool_unknown_name_raises_value_error():
    from orchestrator.tools import execute_tool
    from homelab_common.config import Settings

    with pytest.raises(ValueError, match="Unknown tool"):
        await execute_tool("delete_all_containers", {}, Settings())


def test_available_tools_contain_only_read_only_operations():
    from orchestrator.tools import AVAILABLE_TOOLS

    assert "get_system_resources" in AVAILABLE_TOOLS
    assert "list_containers" in AVAILABLE_TOOLS

    destructive_keywords = {"delete", "stop", "restart", "kill", "exec", "run", "create", "write"}
    for tool_name in AVAILABLE_TOOLS:
        for keyword in destructive_keywords:
            assert keyword not in tool_name.lower(), (
                f"Potentially destructive tool found: {tool_name}"
            )
