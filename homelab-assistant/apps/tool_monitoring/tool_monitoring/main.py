from fastapi import FastAPI
from contextlib import asynccontextmanager

from homelab_common import setup_logging, get_logger, get_settings
from .system import get_system_resources
from .containers import get_containers, ContainerInfo

settings = get_settings()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(settings.log_level, "tool-monitoring")
    logger.info("Monitoring tool service starting")
    yield
    logger.info("Monitoring tool service shutting down")


app = FastAPI(
    title="Homelab Monitoring Tool",
    description="System and container monitoring for homelab assistant",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/health")
async def health():
    """Service health check."""
    return {"status": "healthy", "service": "tool-monitoring"}


@app.get("/system/resources")
async def system_resources():
    """Get current system resource usage."""
    return get_system_resources()


@app.get("/containers", response_model=list[ContainerInfo])
async def containers():
    """List all Docker containers and their status."""
    return get_containers()
