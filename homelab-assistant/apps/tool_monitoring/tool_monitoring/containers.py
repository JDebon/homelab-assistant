from typing import Optional
from pydantic import BaseModel
import docker
from docker.errors import DockerException

from homelab_common import get_logger

logger = get_logger(__name__)


class ContainerInfo(BaseModel):
    id: str
    name: str
    image: str
    status: str
    state: str
    created: str
    ports: dict[str, Optional[list[dict]]]


def get_containers() -> list[ContainerInfo]:
    """Get information about all Docker containers."""
    try:
        client = docker.from_env()
        containers = client.containers.list(all=True)

        result = []
        for container in containers:
            # Parse port mappings
            ports = {}
            if container.attrs.get("NetworkSettings", {}).get("Ports"):
                for port, bindings in container.attrs["NetworkSettings"]["Ports"].items():
                    if bindings:
                        ports[port] = [
                            {"host_ip": b.get("HostIp", ""), "host_port": b.get("HostPort", "")}
                            for b in bindings
                        ]
                    else:
                        ports[port] = None

            result.append(ContainerInfo(
                id=container.short_id,
                name=container.name,
                image=container.image.tags[0] if container.image.tags else container.image.short_id,
                status=container.status,
                state=container.attrs.get("State", {}).get("Status", "unknown"),
                created=container.attrs.get("Created", ""),
                ports=ports,
            ))

        return result

    except DockerException as e:
        logger.error(f"Failed to connect to Docker: {e}")
        return []
