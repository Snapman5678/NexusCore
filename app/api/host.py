# Gets and stores host system information in Redis. This a safety check to ensure that the host system is not overloaded.
# Default maximum CPU usage is 50% and memory usage is 90%.

from fastapi import APIRouter, HTTPException
from ..models.host import HostResource
from ..utils.redis_client import RedisClient, RedisHostResourceMonitor
from pydantic import BaseModel

router = APIRouter()
redis_client = RedisClient.get_instance()


class HostLimits(BaseModel):
    cpu_limit_percent: float
    memory_limit_percent: float


@router.get("/resources", response_model=HostResource)
async def get_host_resources():
    """Get current host system resource metrics"""
    redis_host_monitor = RedisHostResourceMonitor(redis_client=redis_client)
    host_resources = redis_host_monitor.get_latest_resources()

    if not host_resources:
        raise HTTPException(status_code=404, detail="Host resources not found")
    return host_resources


@router.put("/resources/limits", response_model=HostLimits)
async def update_host_limits(limits: HostLimits):
    """Update CPU and memory usage limits"""
    try:
        redis_host_monitor = RedisHostResourceMonitor(redis_client=redis_client)
        if limits.cpu_limit_percent > 90:
            raise HTTPException(status_code=400, detail="CPU limit cannot exceed 90%")
        if limits.memory_limit_percent > 90:
            raise HTTPException(
                status_code=400, detail="Memory limit cannot exceed 90%"
            )

        redis_host_monitor.update_limits(
            limits.cpu_limit_percent, limits.memory_limit_percent
        )
        return limits
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to update limits: {str(e)}"
        )
