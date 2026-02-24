import json
from typing import Any, Optional

from openai import AsyncOpenAI

from homelab_schemas import LLMResponse, ToolDefinition
from .base import BaseLLMProvider


class GroqProvider(BaseLLMProvider):
    """Groq API provider implementation (OpenAI-compatible)."""

    def __init__(self, api_key: str, model: str = "llama-3.3-70b-versatile"):
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = model

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[ToolDefinition],
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Send a chat request to Groq."""

        # Build messages list
        request_messages = []

        if system_prompt:
            request_messages.append({
                "role": "system",
                "content": system_prompt,
            })

        request_messages.extend(messages)

        # Build request kwargs
        kwargs = {
            "model": self.model,
            "messages": request_messages,
        }

        # Add tools if provided
        if tools:
            kwargs["tools"] = [tool.to_openai_function() for tool in tools]

        # Make the API call
        response = await self.client.chat.completions.create(**kwargs)

        # Parse the response
        choice = response.choices[0]
        message = choice.message

        tool_calls = []
        if message.tool_calls:
            for tc in message.tool_calls:
                tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": json.loads(tc.function.arguments),
                })

        return LLMResponse(
            content=message.content,
            tool_calls=tool_calls,
            finish_reason=choice.finish_reason,
        )
