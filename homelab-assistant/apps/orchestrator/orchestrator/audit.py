import json
from datetime import datetime, timezone
from pathlib import Path

from homelab_common import get_logger, get_settings

logger = get_logger(__name__)
settings = get_settings()


async def write_audit_log(
    conversation_id: str,
    user_message: str,
    assistant_response: str,
    tool_calls: list[str],
) -> None:
    """Write an audit log entry to the append-only log file."""

    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "conversation_id": conversation_id,
        "user_message": user_message,
        "assistant_response": assistant_response,
        "tool_calls": tool_calls,
    }

    log_path = Path(settings.audit_log_path)

    try:
        # Ensure directory exists
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # Append to log file
        with open(log_path, "a") as f:
            f.write(json.dumps(log_entry) + "\n")

        logger.debug(f"Audit log written for conversation {conversation_id}")

    except OSError as e:
        logger.error(f"Failed to write audit log: {e}")
