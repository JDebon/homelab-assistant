import psutil
from pydantic import BaseModel


class DiskUsage(BaseModel):
    path: str
    total_gb: float
    used_gb: float
    free_gb: float
    percent_used: float


class SystemResources(BaseModel):
    cpu_percent: float
    memory_total_gb: float
    memory_used_gb: float
    memory_percent: float
    disk: list[DiskUsage]
    load_average: tuple[float, float, float]


def get_system_resources() -> SystemResources:
    """Collect current system resource metrics."""
    # CPU
    cpu_percent = psutil.cpu_percent(interval=0.1)

    # Memory
    memory = psutil.virtual_memory()
    memory_total_gb = round(memory.total / (1024**3), 2)
    memory_used_gb = round(memory.used / (1024**3), 2)

    # Disk - get all mounted partitions
    disk_usage = []
    for partition in psutil.disk_partitions():
        try:
            usage = psutil.disk_usage(partition.mountpoint)
            # Only include significant partitions
            if usage.total > 1024**3:  # > 1GB
                disk_usage.append(DiskUsage(
                    path=partition.mountpoint,
                    total_gb=round(usage.total / (1024**3), 2),
                    used_gb=round(usage.used / (1024**3), 2),
                    free_gb=round(usage.free / (1024**3), 2),
                    percent_used=usage.percent,
                ))
        except PermissionError:
            continue

    # Load average
    load_avg = psutil.getloadavg()

    return SystemResources(
        cpu_percent=cpu_percent,
        memory_total_gb=memory_total_gb,
        memory_used_gb=memory_used_gb,
        memory_percent=memory.percent,
        disk=disk_usage,
        load_average=load_avg,
    )
