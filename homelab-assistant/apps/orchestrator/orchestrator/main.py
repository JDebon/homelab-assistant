import uuid
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
import httpx

from homelab_common import setup_logging, get_logger, get_settings
from homelab_schemas import ChatRequest, ChatResponse, LLMRequest, LLMResponse
from .tools import AVAILABLE_TOOLS, execute_tool
from .audit import write_audit_log
from .database import init_db, record_session, get_enabled_tools

settings = get_settings()
logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a helpful homelab assistant. You help users monitor and understand their homelab infrastructure.

You have access to monitoring tools that allow you to:
- Check system resources (CPU, memory, disk usage)
- List Docker containers and their status

IMPORTANT SAFETY RULES:
1. You can ONLY use the monitoring tools provided to you
2. You CANNOT execute any commands that modify the system
3. You CANNOT restart, stop, or modify containers
4. You CANNOT execute arbitrary shell commands
5. If a user asks you to perform any destructive or modifying action, politely refuse and explain that you can only monitor the system

Always be helpful and provide clear explanations of the monitoring data you retrieve."""


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level, "orchestrator")
    logger.info("Orchestrator service starting")
    await init_db(settings.db_path)
    yield
    logger.info("Orchestrator service shutting down")


app = FastAPI(
    title="Homelab Orchestrator",
    description="Core orchestration service for homelab assistant",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Service health check."""
    return {"status": "healthy", "service": "orchestrator"}


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Process a chat request from the user."""
    conversation_id = request.conversation_id or str(uuid.uuid4())

    logger.info(f"Processing chat request: conversation_id={conversation_id}")

    await record_session(settings.db_path, conversation_id)
    enabled_tools = await get_enabled_tools(settings.db_path)

    # Build the messages for the LLM
    messages = [{"role": "user", "content": request.message}]

    # Get tool definitions
    tools = list(AVAILABLE_TOOLS.values())

    tool_calls_made = []
    max_iterations = 5  # Prevent infinite loops

    async with httpx.AsyncClient(timeout=60.0) as client:
        for iteration in range(max_iterations):
            # Call the LLM adapter
            llm_request = LLMRequest(
                messages=messages,
                tools=tools,
                system_prompt=SYSTEM_PROMPT,
            )

            try:
                llm_response = await client.post(
                    f"{settings.llm_adapter_url}/chat",
                    json=llm_request.model_dump(),
                )
                llm_response.raise_for_status()
                llm_data = LLMResponse(**llm_response.json())
            except httpx.HTTPError as e:
                logger.error(f"LLM adapter request failed: {e}")
                raise HTTPException(status_code=502, detail="LLM service unavailable")

            # If no tool calls, we're done
            if not llm_data.tool_calls:
                final_response = llm_data.content or "I apologize, but I couldn't generate a response."

                # Write audit log
                await write_audit_log(
                    conversation_id=conversation_id,
                    user_message=request.message,
                    assistant_response=final_response,
                    tool_calls=tool_calls_made,
                )

                return ChatResponse(
                    message=final_response,
                    conversation_id=conversation_id,
                    tool_calls_made=tool_calls_made,
                )

            # Execute tool calls
            tool_results = []
            for tool_call in llm_data.tool_calls:
                tool_name = tool_call["name"]
                tool_args = tool_call["arguments"]
                tool_id = tool_call["id"]

                logger.info(f"Executing tool: {tool_name}")
                tool_calls_made.append(tool_name)

                try:
                    result = await execute_tool(tool_name, tool_args, settings, enabled_tools)
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": str(result),
                    })
                except ValueError as e:
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": f"Error: {e}",
                    })

            # Add assistant message with tool calls and tool results to conversation
            messages.append({
                "role": "assistant",
                "content": llm_data.content,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": str(tc["arguments"]),
                        },
                    }
                    for tc in llm_data.tool_calls
                ],
            })
            messages.extend(tool_results)

    # If we hit max iterations
    logger.warning(f"Max iterations reached for conversation {conversation_id}")
    return ChatResponse(
        message="I apologize, but I wasn't able to complete your request. Please try again.",
        conversation_id=conversation_id,
        tool_calls_made=tool_calls_made,
    )
