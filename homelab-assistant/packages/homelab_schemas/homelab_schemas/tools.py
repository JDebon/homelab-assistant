from typing import Any, Optional
from pydantic import BaseModel, Field


class ToolParameter(BaseModel):
    """Parameter definition for a tool."""
    name: str
    type: str
    description: str
    required: bool = True
    enum: Optional[list[str]] = None


class ToolDefinition(BaseModel):
    """Definition of an available tool."""
    name: str
    description: str
    parameters: list[ToolParameter] = Field(default_factory=list)

    def to_openai_function(self) -> dict:
        """Convert to OpenAI function calling format."""
        properties = {}
        required = []

        for param in self.parameters:
            prop = {
                "type": param.type,
                "description": param.description,
            }
            if param.enum:
                prop["enum"] = param.enum
            properties[param.name] = prop

            if param.required:
                required.append(param.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


class LLMRequest(BaseModel):
    """Request to the LLM adapter."""
    messages: list[dict[str, Any]]
    tools: list[ToolDefinition] = Field(default_factory=list)
    system_prompt: Optional[str] = None


class LLMResponse(BaseModel):
    """Response from the LLM adapter."""
    content: Optional[str] = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    finish_reason: str
