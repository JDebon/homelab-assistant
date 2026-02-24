from abc import ABC, abstractmethod
from typing import Any, Optional

from homelab_schemas import LLMResponse, ToolDefinition


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition],
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """
        Send a chat request to the LLM.

        Args:
            messages: List of conversation messages
            tools: Available tool definitions
            system_prompt: Optional system prompt

        Returns:
            LLMResponse with content and/or tool calls
        """
        pass
