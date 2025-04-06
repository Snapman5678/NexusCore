from fastapi import APIRouter, HTTPException
from typing import List
from ..models.pod import Pod, PodCreation, PodStatus
from ..core.scheduler import Scheduler
from ..utils.redis_client import RedisClient

router = APIRouter()
scheduler = Scheduler()
redis_client = RedisClient.get_instance()


@router.post("/", response_model=Pod, status_code=201)
async def launch_pod(pod_creation: PodCreation):
    """Launch a new pod with specified CPU and memory requirements"""
    try:
        # Create a new pod instance
        pod = Pod(name=pod_creation.name, resources=pod_creation.resources)

        # Use the scheduler to find a suitable node
        assigned_node = scheduler.schedule_pod(pod)
        if assigned_node:
            pod.node_id = assigned_node.id
            pod.status = PodStatus.RUNNING
            redis_client.store_pod(pod)
            return pod
        else:
            pod.status = PodStatus.PENDING
            redis_client.store_pod(pod)
            raise HTTPException(
                status_code=503,
                detail="No nodes available with sufficient CPU and memory",
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to launch pod: {str(e)}")


@router.get("/", response_model=List[Pod])
async def list_pods():
    """List all pods in the cluster"""
    try:
        pods = redis_client.get_all_pods()
        return pods
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve pods: {str(e)}"
        )


@router.get("/{pod_id}", response_model=Pod)
async def get_pod(pod_id: str):
    """Get details of a specific pod"""
    pod = redis_client.get_pod(pod_id)
    if not pod:
        raise HTTPException(status_code=404, detail=f"Pod {pod_id} not found")
    return pod


@router.delete("/{pod_id}", status_code=204)
async def delete_pod(pod_id: str):
    """Delete a pod and free its resources"""
    pod = redis_client.get_pod(pod_id)
    if not pod:
        raise HTTPException(status_code=404, detail=f"Pod {pod_id} not found")

    redis_client.delete_pod(pod_id)
    return None
