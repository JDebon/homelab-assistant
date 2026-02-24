from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


class Role(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ToolCall(BaseModel):
    """A tool call requested by the LLM."""
    id: str
    name: str
    arguments: dict[str, Any]


class ToolResult(BaseModel):
    """Result from executing a tool."""
    tool_call_id: str
    name: str
    result: Any
    error: Optional[str] = None


class Message(BaseModel):
    """A message in the conversation."""
    role: Role
    content: str
    tool_calls: Optional[list[ToolCall]] = None
    tool_results: Optional[list[ToolResult]] = None


class ChatRequest(BaseModel):
    """Request to the assistant."""
    message: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response from the assistant."""
    message: str
    conversation_id: str
    tool_calls_made: list[str] = Field(default_factory=list)
