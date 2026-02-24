"""Tests for the Gateway service."""
import pytest
from unittest.mock import AsyncMock, MagicMock

import httpx
from httpx import AsyncClient, ASGITransport


@pytest.fixture(autouse=True)
def clear_rate_limit_store():
    from gateway.main import rate_limit_store

    rate_limit_store.clear()
    yield
    rate_limit_store.clear()


@pytest.fixture
def mock_settings(mocker):
    mock = MagicMock()
    mock.api_key = "test-api-key"
    mock.rate_limit_requests = 60
    mock.rate_limit_window = 60
    mock.orchestrator_url = "http://test-orchestrator:8001"
    mocker.patch("gateway.main.settings", mock)
    return mock


@pytest.fixture
async def gateway_client(mock_settings):
    from gateway.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client


async def test_health_endpoint(gateway_client):
    response = await gateway_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "gateway"


async def test_chat_missing_api_key_returns_401(gateway_client):
    response = await gateway_client.post("/chat", json={"message": "hello"})
    assert response.status_code == 401


async def test_chat_invalid_api_key_returns_401(gateway_client):
    response = await gateway_client.post(
        "/chat",
        json={"message": "hello"},
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401


async def test_chat_valid_key_forwards_to_orchestrator(gateway_client, mocker):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "message": "All systems nominal",
        "conversation_id": "conv-123",
        "tool_calls_made": [],
    }
    mock_http = AsyncMock()
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None
    mock_http.post.return_value = mock_resp
    mocker.patch("gateway.main.httpx.AsyncClient", return_value=mock_http)

    response = await gateway_client.post(
        "/chat",
        json={"message": "Is everything running?"},
        headers={"X-API-Key": "test-api-key"},
    )

    assert response.status_code == 200
    assert response.json()["message"] == "All systems nominal"
    mock_http.post.assert_called_once()


async def test_chat_forwards_correct_payload(gateway_client, mocker):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {
        "message": "ok",
        "conversation_id": "conv-1",
        "tool_calls_made": [],
    }
    mock_http = AsyncMock()
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None
    mock_http.post.return_value = mock_resp
    mocker.patch("gateway.main.httpx.AsyncClient", return_value=mock_http)

    await gateway_client.post(
        "/chat",
        json={"message": "hello", "conversation_id": "my-conv"},
        headers={"X-API-Key": "test-api-key"},
    )

    _, call_kwargs = mock_http.post.call_args
    payload = call_kwargs["json"]
    assert payload["message"] == "hello"
    assert payload["conversation_id"] == "my-conv"


async def test_chat_rate_limit_exceeded(gateway_client, mock_settings, mocker):
    mock_settings.rate_limit_requests = 2

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status = MagicMock()
    mock_resp.json.return_value = {"message": "ok", "conversation_id": "c", "tool_calls_made": []}
    mock_http = AsyncMock()
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None
    mock_http.post.return_value = mock_resp
    mocker.patch("gateway.main.httpx.AsyncClient", return_value=mock_http)

    for _ in range(2):
        r = await gateway_client.post(
            "/chat",
            json={"message": "hi"},
            headers={"X-API-Key": "test-api-key"},
        )
        assert r.status_code == 200

    r = await gateway_client.post(
        "/chat",
        json={"message": "hi"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert r.status_code == 429


async def test_chat_orchestrator_unreachable_returns_502(gateway_client, mocker):
    mock_http = AsyncMock()
    mock_http.__aenter__.return_value = mock_http
    mock_http.__aexit__.return_value = None
    mock_http.post.side_effect = httpx.RequestError("connection refused")
    mocker.patch("gateway.main.httpx.AsyncClient", return_value=mock_http)

    response = await gateway_client.post(
        "/chat",
        json={"message": "hello"},
        headers={"X-API-Key": "test-api-key"},
    )
    assert response.status_code == 502


def test_rate_limit_allows_requests_within_window(mock_settings):
    from gateway.main import check_rate_limit, rate_limit_store

    rate_limit_store.clear()
    mock_settings.rate_limit_requests = 3
    mock_settings.rate_limit_window = 60

    assert check_rate_limit("key1") is True
    assert check_rate_limit("key1") is True
    assert check_rate_limit("key1") is True
    assert check_rate_limit("key1") is False  # 4th request exceeds limit


def test_rate_limit_is_independent_per_key(mock_settings):
    from gateway.main import check_rate_limit, rate_limit_store

    rate_limit_store.clear()
    mock_settings.rate_limit_requests = 1
    mock_settings.rate_limit_window = 60

    assert check_rate_limit("key-a") is True
    assert check_rate_limit("key-a") is False
    assert check_rate_limit("key-b") is True  # different key has its own quota
