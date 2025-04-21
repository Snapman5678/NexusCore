from fastapi import APIRouter, HTTPException
from typing import Dict
# from ..core.fault_tolerance import ResourceFailureHandler
from ..models.node import NodeStatus, NodeResources
from ..core.node_manager import NodeManager
from pydantic import BaseModel

router = APIRouter()
node_manager = NodeManager()
# resource_handler = ResourceFailureHandler()


class ResourceUtilization(BaseModel):
    cpu_utilization: float
    memory_utilization: float


class ClusterHealth(BaseModel):
    total_nodes: int
    online_nodes: int
    total_cpu_cores: int
    total_memory_gb: float
    average_cpu_utilization: float
    average_memory_utilization: float
    nodes_utilization: Dict[str, ResourceUtilization]


class HeartbeatRequest(BaseModel):
    resources: NodeResources
    status: str = "online"


@router.post("/heartbeat/{node_id}")
async def send_heartbeat(node_id: str, heartbeat: HeartbeatRequest):
    """Receive node heartbeat with resource metrics"""
    try:
        node = node_manager.update_node_resources(node_id, heartbeat.resources)
        if not node:
            raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

        if heartbeat.status == "online":
            node_manager.update_node_status(node_id, NodeStatus.ONLINE)

        return {"received": True, "message": "Resource metrics updated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to process heartbeat: {str(e)}"
        )
