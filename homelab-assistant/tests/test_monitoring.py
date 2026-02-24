"""Tests for the Tool Monitoring service."""
import pytest
from unittest.mock import MagicMock
from httpx import AsyncClient, ASGITransport


async def test_health_endpoint():
    from tool_monitoring.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "tool-monitoring"


class TestGetSystemResources:
    def _patch_psutil(self, mocker, *, cpu=30.0, mem_total_gb=16, mem_used_gb=4, mem_pct=25.0,
                     partitions=None, disk_usage_side_effect=None, loadavg=(1.0, 0.8, 0.6)):
        mock_memory = MagicMock()
        mock_memory.total = mem_total_gb * 1024**3
        mock_memory.used = mem_used_gb * 1024**3
        mock_memory.percent = mem_pct

        mocker.patch("tool_monitoring.system.psutil.cpu_percent", return_value=cpu)
        mocker.patch("tool_monitoring.system.psutil.virtual_memory", return_value=mock_memory)
        mocker.patch("tool_monitoring.system.psutil.disk_partitions",
                     return_value=partitions or [])
        if disk_usage_side_effect is not None:
            mocker.patch("tool_monitoring.system.psutil.disk_usage",
                         side_effect=disk_usage_side_effect)
        mocker.patch("tool_monitoring.system.psutil.getloadavg", return_value=loadavg)

    def test_returns_system_resources_model(self, mocker):
        mock_partition = MagicMock()
        mock_partition.mountpoint = "/"
        mock_disk = MagicMock()
        mock_disk.total = 500 * 1024**3
        mock_disk.used = 100 * 1024**3
        mock_disk.free = 400 * 1024**3
        mock_disk.percent = 20.0

        self._patch_psutil(
            mocker,
            cpu=30.0,
            mem_total_gb=16,
            mem_used_gb=4,
            mem_pct=25.0,
            partitions=[mock_partition],
            disk_usage_side_effect=[mock_disk],
            loadavg=(1.0, 0.8, 0.6),
        )

        from tool_monitoring.system import get_system_resources

        result = get_system_resources()

        assert result.cpu_percent == 30.0
        assert result.memory_total_gb == 16.0
        assert result.memory_used_gb == 4.0
        assert result.memory_percent == 25.0
        assert result.load_average == (1.0, 0.8, 0.6)

    def test_disk_smaller_than_1gb_is_excluded(self, mocker):
        small_partition = MagicMock()
        small_partition.mountpoint = "/boot"
        large_partition = MagicMock()
        large_partition.mountpoint = "/"

        small_disk = MagicMock()
        small_disk.total = 512 * 1024**2  # 512 MB

        large_disk = MagicMock()
        large_disk.total = 200 * 1024**3  # 200 GB
        large_disk.used = 50 * 1024**3
        large_disk.free = 150 * 1024**3
        large_disk.percent = 25.0

        self._patch_psutil(
            mocker,
            partitions=[small_partition, large_partition],
            disk_usage_side_effect=[small_disk, large_disk],
        )

        from tool_monitoring.system import get_system_resources

        result = get_system_resources()

        assert len(result.disk) == 1
        assert result.disk[0].path == "/"

    def test_permission_error_on_partition_is_skipped(self, mocker):
        partition = MagicMock()
        partition.mountpoint = "/proc"

        self._patch_psutil(
            mocker,
            partitions=[partition],
            disk_usage_side_effect=PermissionError,
        )

        from tool_monitoring.system import get_system_resources

        result = get_system_resources()

        assert result.disk == []


class TestGetContainers:
    def test_returns_container_info_list(self, mocker):
        mock_container = MagicMock()
        mock_container.short_id = "abc123def"
        mock_container.name = "homelab-gateway"
        mock_container.image.tags = ["homelab-gateway:latest"]
        mock_container.status = "running"
        mock_container.attrs = {
            "State": {"Status": "running"},
            "Created": "2024-01-01T00:00:00Z",
            "NetworkSettings": {
                "Ports": {"8000/tcp": [{"HostIp": "0.0.0.0", "HostPort": "8000"}]}
            },
        }

        mock_docker = MagicMock()
        mock_docker.containers.list.return_value = [mock_container]
        mocker.patch("tool_monitoring.containers.docker.from_env", return_value=mock_docker)

        from tool_monitoring.containers import get_containers

        result = get_containers()

        assert len(result) == 1
        c = result[0]
        assert c.id == "abc123def"
        assert c.name == "homelab-gateway"
        assert c.image == "homelab-gateway:latest"
        assert c.status == "running"
        assert c.state == "running"
        assert "8000/tcp" in c.ports

    def test_container_without_image_tags_falls_back_to_short_id(self, mocker):
        mock_container = MagicMock()
        mock_container.short_id = "xyz789"
        mock_container.name = "unnamed-container"
        mock_container.image.tags = []
        mock_container.image.short_id = "sha256:abc"
        mock_container.status = "exited"
        mock_container.attrs = {
            "State": {"Status": "exited"},
            "Created": "2024-01-01T00:00:00Z",
            "NetworkSettings": {"Ports": {}},
        }

        mock_docker = MagicMock()
        mock_docker.containers.list.return_value = [mock_container]
        mocker.patch("tool_monitoring.containers.docker.from_env", return_value=mock_docker)

        from tool_monitoring.containers import get_containers

        result = get_containers()

        assert result[0].image == "sha256:abc"

    def test_docker_unavailable_returns_empty_list(self, mocker):
        from docker.errors import DockerException

        mocker.patch(
            "tool_monitoring.containers.docker.from_env",
            side_effect=DockerException("Docker socket not found"),
        )

        from tool_monitoring.containers import get_containers

        result = get_containers()

        assert result == []

    def test_list_includes_stopped_containers(self, mocker):
        mock_docker = MagicMock()
        mock_docker.containers.list.return_value = []
        mocker.patch("tool_monitoring.containers.docker.from_env", return_value=mock_docker)

        from tool_monitoring.containers import get_containers

        get_containers()

        mock_docker.containers.list.assert_called_once_with(all=True)


async def test_system_resources_endpoint(mocker):
    from tool_monitoring.system import SystemResources, DiskUsage

    mock_resources = SystemResources(
        cpu_percent=30.0,
        memory_total_gb=16.0,
        memory_used_gb=4.0,
        memory_percent=25.0,
        disk=[
            DiskUsage(path="/", total_gb=500.0, used_gb=100.0, free_gb=400.0, percent_used=20.0)
        ],
        load_average=(1.0, 0.8, 0.6),
    )
    mocker.patch("tool_monitoring.main.get_system_resources", return_value=mock_resources)

    from tool_monitoring.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/system/resources")

    assert response.status_code == 200
    data = response.json()
    assert data["cpu_percent"] == 30.0
    assert data["memory_percent"] == 25.0
    assert len(data["disk"]) == 1
    assert data["disk"][0]["path"] == "/"


async def test_containers_endpoint(mocker):
    from tool_monitoring.containers import ContainerInfo

    mock_containers = [
        ContainerInfo(
            id="abc123",
            name="test-container",
            image="test:latest",
            status="running",
            state="running",
            created="2024-01-01T00:00:00Z",
            ports={},
        )
    ]
    mocker.patch("tool_monitoring.main.get_containers", return_value=mock_containers)

    from tool_monitoring.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/containers")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["name"] == "test-container"
    assert data[0]["status"] == "running"
