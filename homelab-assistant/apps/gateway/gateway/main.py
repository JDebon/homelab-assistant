import time
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import httpx

from homelab_common import setup_logging, get_logger, get_settings
from homelab_schemas import ChatRequest, ChatResponse

settings = get_settings()
logger = get_logger(__name__)

# Simple in-memory rate limiting
rate_limit_store: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(api_key: str) -> bool:
    """Check if the request is within rate limits."""
    now = time.time()
    window_start = now - settings.rate_limit_window

    # Clean old entries
    rate_limit_store[api_key] = [
        ts for ts in rate_limit_store[api_key] if ts > window_start
    ]

    # Check limit
    if len(rate_limit_store[api_key]) >= settings.rate_limit_requests:
        return False

    # Record this request
    rate_limit_store[api_key].append(now)
    return True


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level, "gateway")
    logger.info("Gateway service starting")

    if not settings.api_key:
        logger.warning("API_KEY not set - authentication disabled")

    yield
    logger.info("Gateway service shutting down")


app = FastAPI(
    title="Homelab Assistant Gateway",
    description="API gateway for homelab assistant",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST", "GET"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    """Service health check (no auth required)."""
    return {"status": "healthy", "service": "gateway"}


@app.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    x_api_key: str = Header(None, alias="X-API-Key"),
):
    """
    Send a chat message to the assistant.

    Requires X-API-Key header for authentication.
    """
    # Authentication
    if settings.api_key:
        if not x_api_key:
            raise HTTPException(status_code=401, detail="Missing API key")
        if x_api_key != settings.api_key:
            raise HTTPException(status_code=401, detail="Invalid API key")

    # Rate limiting
    rate_key = x_api_key or "anonymous"
    if not check_rate_limit(rate_key):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Max {settings.rate_limit_requests} requests per {settings.rate_limit_window} seconds",
        )

    # Forward to orchestrator
    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(
                f"{settings.orchestrator_url}/chat",
                json=request.model_dump(),
            )
            response.raise_for_status()
            return ChatResponse(**response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"Orchestrator returned error: {e.response.status_code}")
            raise HTTPException(
                status_code=e.response.status_code,
                detail=e.response.text,
            )
        except httpx.RequestError as e:
            logger.error(f"Failed to reach orchestrator: {e}")
            raise HTTPException(status_code=502, detail="Backend service unavailable")
