"""Tests for the audit logging module."""
import json

from unittest.mock import MagicMock


async def test_audit_log_creates_file(tmp_path, mocker):
    log_path = tmp_path / "audit.jsonl"
    mock_settings = MagicMock()
    mock_settings.audit_log_path = str(log_path)
    mocker.patch("orchestrator.audit.settings", mock_settings)

    from orchestrator.audit import write_audit_log

    await write_audit_log(
        conversation_id="conv-123",
        user_message="What is CPU usage?",
        assistant_response="CPU is at 25%.",
        tool_calls=["get_system_resources"],
    )

    assert log_path.exists()


async def test_audit_log_writes_valid_jsonl(tmp_path, mocker):
    log_path = tmp_path / "audit.jsonl"
    mock_settings = MagicMock()
    mock_settings.audit_log_path = str(log_path)
    mocker.patch("orchestrator.audit.settings", mock_settings)

    from orchestrator.audit import write_audit_log

    await write_audit_log(
        conversation_id="conv-abc",
        user_message="How many containers are running?",
        assistant_response="There are 5 containers.",
        tool_calls=["list_containers"],
    )

    entry = json.loads(log_path.read_text().strip())
    assert entry["conversation_id"] == "conv-abc"
    assert entry["user_message"] == "How many containers are running?"
    assert entry["assistant_response"] == "There are 5 containers."
    assert entry["tool_calls"] == ["list_containers"]
    assert "timestamp" in entry


async def test_audit_log_appends_multiple_entries(tmp_path, mocker):
    log_path = tmp_path / "audit.jsonl"
    mock_settings = MagicMock()
    mock_settings.audit_log_path = str(log_path)
    mocker.patch("orchestrator.audit.settings", mock_settings)

    from orchestrator.audit import write_audit_log

    await write_audit_log("conv-1", "message 1", "response 1", [])
    await write_audit_log("conv-2", "message 2", "response 2", [])
    await write_audit_log("conv-3", "message 3", "response 3", [])

    lines = log_path.read_text().strip().split("\n")
    assert len(lines) == 3
    ids = [json.loads(line)["conversation_id"] for line in lines]
    assert ids == ["conv-1", "conv-2", "conv-3"]


async def test_audit_log_creates_parent_directories(tmp_path, mocker):
    nested_path = tmp_path / "logs" / "homelab" / "audit.jsonl"
    mock_settings = MagicMock()
    mock_settings.audit_log_path = str(nested_path)
    mocker.patch("orchestrator.audit.settings", mock_settings)

    from orchestrator.audit import write_audit_log

    await write_audit_log("conv-x", "msg", "resp", [])

    assert nested_path.exists()


async def test_audit_log_handles_os_error_gracefully(tmp_path, mocker):
    log_path = tmp_path / "audit.jsonl"
    mock_settings = MagicMock()
    mock_settings.audit_log_path = str(log_path)
    mocker.patch("orchestrator.audit.settings", mock_settings)
    mocker.patch("orchestrator.audit.open", side_effect=OSError("No space left on device"))

    from orchestrator.audit import write_audit_log

    # Must not raise even when write fails
    await write_audit_log("conv-err", "msg", "resp", [])
