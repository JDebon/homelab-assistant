from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager

from homelab_common import setup_logging, get_logger, get_settings
from homelab_schemas import LLMRequest, LLMResponse
from .providers.openai_provider import OpenAIProvider
from .providers.groq_provider import GroqProvider

settings = get_settings()
logger = get_logger(__name__)

provider = None
provider_name = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global provider, provider_name
    setup_logging(settings.log_level, "llm-adapter")
    logger.info("LLM Adapter service starting")

    if settings.llm_provider == "groq":
        if not settings.groq_api_key:
            logger.warning("GROQ_API_KEY not set - service will fail on requests")
        else:
            provider = GroqProvider(api_key=settings.groq_api_key)
            provider_name = "groq"
            logger.info("Groq provider initialized")
    else:
        if not settings.openai_api_key:
            logger.warning("OPENAI_API_KEY not set - service will fail on requests")
        else:
            provider = OpenAIProvider(api_key=settings.openai_api_key)
            provider_name = "openai"
            logger.info("OpenAI provider initialized")

    yield
    logger.info("LLM Adapter service shutting down")


app = FastAPI(
    title="Homelab LLM Adapter",
    description="LLM abstraction layer for homelab assistant",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Service health check."""
    return {
        "status": "healthy",
        "service": "llm-adapter",
        "provider": provider_name if provider else "none",
    }


@app.post("/chat", response_model=LLMResponse)
async def chat(request: LLMRequest):
    """Send a chat request to the LLM."""
    if not provider:
        raise HTTPException(status_code=503, detail="LLM provider not configured")

    try:
        response = await provider.chat(
            messages=request.messages,
            tools=request.tools,
            system_prompt=request.system_prompt,
        )
        return response
    except Exception as e:
        logger.error(f"LLM request failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
