"""Tests for the orchestrator database module."""
import pytest
import aiosqlite


@pytest.fixture
async def db_path(tmp_path):
    """Create a fresh temporary database for each test."""
    from orchestrator.database import init_db

    path = str(tmp_path / "test.db")
    await init_db(path)
    return path


async def test_init_db_creates_all_tables(db_path):
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = {row[0] for row in await cursor.fetchall()}
    assert {"users", "sessions", "configuration", "enabled_tools"} <= tables


async def test_init_db_seeds_default_tools(db_path):
    from orchestrator.database import get_enabled_tools

    tools = await get_enabled_tools(db_path)
    assert "get_system_resources" in tools
    assert "list_containers" in tools


async def test_init_db_is_idempotent(db_path):
    from orchestrator.database import init_db, get_enabled_tools

    await init_db(db_path)  # second call must not fail or duplicate rows
    tools = await get_enabled_tools(db_path)
    assert len(tools) == 2


async def test_record_session_creates_new_session(db_path):
    from orchestrator.database import record_session

    await record_session(db_path, "conv-001")

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT message_count FROM sessions WHERE conversation_id = ?",
            ("conv-001",),
        )
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] == 1


async def test_record_session_increments_message_count(db_path):
    from orchestrator.database import record_session

    await record_session(db_path, "conv-002")
    await record_session(db_path, "conv-002")
    await record_session(db_path, "conv-002")

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT message_count FROM sessions WHERE conversation_id = ?",
            ("conv-002",),
        )
        row = await cursor.fetchone()

    assert row[0] == 3


async def test_record_session_updates_last_active_at(db_path):
    from orchestrator.database import record_session

    await record_session(db_path, "conv-003")

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT created_at, last_active_at FROM sessions WHERE conversation_id = ?",
            ("conv-003",),
        )
        row = await cursor.fetchone()

    assert row is not None
    assert row[0] is not None  # created_at set
    assert row[1] is not None  # last_active_at set


async def test_record_session_multiple_conversations_are_independent(db_path):
    from orchestrator.database import record_session

    await record_session(db_path, "conv-a")
    await record_session(db_path, "conv-a")
    await record_session(db_path, "conv-b")

    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT conversation_id, message_count FROM sessions ORDER BY conversation_id"
        )
        rows = dict(await cursor.fetchall())

    assert rows["conv-a"] == 2
    assert rows["conv-b"] == 1


async def test_get_enabled_tools_returns_set(db_path):
    from orchestrator.database import get_enabled_tools

    tools = await get_enabled_tools(db_path)
    assert isinstance(tools, set)


async def test_get_enabled_tools_excludes_disabled_tools(db_path):
    from orchestrator.database import get_enabled_tools

    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            "UPDATE enabled_tools SET is_enabled = 0 WHERE tool_name = 'list_containers'"
        )
        await db.commit()

    tools = await get_enabled_tools(db_path)
    assert "list_containers" not in tools
    assert "get_system_resources" in tools


async def test_get_enabled_tools_empty_when_all_disabled(db_path):
    from orchestrator.database import get_enabled_tools

    async with aiosqlite.connect(db_path) as db:
        await db.execute("UPDATE enabled_tools SET is_enabled = 0")
        await db.commit()

    tools = await get_enabled_tools(db_path)
    assert len(tools) == 0


async def test_execute_tool_respects_enabled_tools_set(mocker):
    from orchestrator.tools import execute_tool
    from homelab_common.config import Settings

    # Only get_system_resources is enabled — list_containers should be rejected
    with pytest.raises(ValueError, match="Unknown tool"):
        await execute_tool("list_containers", {}, Settings(), {"get_system_resources"})


async def test_execute_tool_unknown_tool_raises_with_enabled_tools(mocker):
    from orchestrator.tools import execute_tool
    from homelab_common.config import Settings

    with pytest.raises(ValueError, match="Unknown tool"):
        await execute_tool(
            "nonexistent_tool", {}, Settings(), {"get_system_resources", "list_containers"}
        )
