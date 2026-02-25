import aiosqlite

from homelab_common import get_logger

logger = get_logger(__name__)

DEFAULT_TOOLS = ["get_system_resources", "list_containers"]


async def init_db(db_path: str) -> None:
    """Create tables and seed defaults if not present."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                api_key_hash TEXT NOT NULL UNIQUE,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                conversation_id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                last_active_at TEXT NOT NULL DEFAULT (datetime('now')),
                message_count INTEGER NOT NULL DEFAULT 0
            )
        """)
        await db.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_last_active
            ON sessions (last_active_at)
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS configuration (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS enabled_tools (
                tool_name TEXT PRIMARY KEY,
                is_enabled INTEGER NOT NULL DEFAULT 1,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        for tool_name in DEFAULT_TOOLS:
            await db.execute(
                "INSERT OR IGNORE INTO enabled_tools (tool_name, is_enabled) VALUES (?, 1)",
                (tool_name,),
            )
        await db.commit()
    logger.info("Database initialized at %s", db_path)


async def record_session(db_path: str, conversation_id: str) -> None:
    """Create a new session or increment message count for an existing one."""
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO sessions (conversation_id, created_at, last_active_at, message_count)
            VALUES (?, datetime('now'), datetime('now'), 1)
            ON CONFLICT(conversation_id) DO UPDATE SET
                last_active_at = datetime('now'),
                message_count = message_count + 1
            """,
            (conversation_id,),
        )
        await db.commit()


async def get_enabled_tools(db_path: str) -> set[str]:
    """Return the set of tool names that are currently enabled."""
    async with aiosqlite.connect(db_path) as db:
        cursor = await db.execute(
            "SELECT tool_name FROM enabled_tools WHERE is_enabled = 1"
        )
        rows = await cursor.fetchall()
        return {row[0] for row in rows}
