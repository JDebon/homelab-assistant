from typing import Any
import httpx

from homelab_schemas import ToolDefinition
from homelab_common import Settings

# Define available tools
AVAILABLE_TOOLS: dict[str, ToolDefinition] = {
    "get_system_resources": ToolDefinition(
        name="get_system_resources",
        description="Get current system resource usage including CPU, memory, and disk space",
        parameters=[],
    ),
    "list_containers": ToolDefinition(
        name="list_containers",
        description="List all Docker containers with their current status, image, and port mappings",
        parameters=[],
    ),
}


async def execute_tool(
    name: str,
    arguments: dict[str, Any],
    settings: Settings,
    enabled_tools: set[str] | None = None,
) -> Any:
    """Execute a tool and return the result."""

    active = enabled_tools if enabled_tools is not None else set(AVAILABLE_TOOLS.keys())
    if name not in active:
        raise ValueError(f"Unknown tool: {name}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        if name == "get_system_resources":
            response = await client.get(f"{settings.monitoring_url}/system/resources")
            response.raise_for_status()
            return response.json()

        elif name == "list_containers":
            response = await client.get(f"{settings.monitoring_url}/containers")
            response.raise_for_status()
            return response.json()

        else:
            raise ValueError(f"Tool not implemented: {name}")
