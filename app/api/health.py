from fastapi import APIRouter, HTTPException
from typing import Dict
from ..core.fault_tolerance import ResourceFailureHandler
from ..models.node import NodeStatus, NodeResources
from ..core.node_manager import NodeManager
from pydantic import BaseModel

router = APIRouter()
node_manager = NodeManager()
resource_handler = ResourceFailureHandler()


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


@router.get("/cluster", response_model=ClusterHealth)
async def get_cluster_health():
    """Get overall cluster health metrics focused on resource utilization"""
    try:
        nodes = node_manager.get_all_nodes()
        online_nodes = [node for node in nodes if node.status == NodeStatus.ONLINE]

        if not nodes:
            raise HTTPException(status_code=404, detail="No nodes found in cluster")

        # Calculate cluster-wide metrics
        total_cpu = sum(node.resources.cpu_count for node in online_nodes)
        total_memory = sum(node.resources.memory_total for node in online_nodes)

        # Get utilization for each node
        nodes_utilization = {}
        total_cpu_util = 0
        total_memory_util = 0

        for node in online_nodes:
            util = resource_handler.get_node_resource_utilization(node)
            nodes_utilization[node.id] = ResourceUtilization(
                cpu_utilization=util["cpu_utilization"],
                memory_utilization=util["memory_utilization"],
            )
            total_cpu_util += util["cpu_utilization"]
            total_memory_util += util["memory_utilization"]

        # Calculate averages
        avg_cpu_util = total_cpu_util / len(online_nodes) if online_nodes else 0
        avg_memory_util = total_memory_util / len(online_nodes) if online_nodes else 0

        return ClusterHealth(
            total_nodes=len(nodes),
            online_nodes=len(online_nodes),
            total_cpu_cores=total_cpu,
            total_memory_gb=total_memory / (1024 * 1024 * 1024),
            average_cpu_utilization=avg_cpu_util,
            average_memory_utilization=avg_memory_util,
            nodes_utilization=nodes_utilization,
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get cluster health: {str(e)}"
        )


@router.get("/nodes/{node_id}", response_model=ResourceUtilization)
async def get_node_health(node_id: str):
    """Get resource utilization metrics for a specific node"""
    node = node_manager.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")

    if node.status != NodeStatus.ONLINE:
        raise HTTPException(status_code=400, detail=f"Node {node_id} is not online")

    try:
        util = resource_handler.get_node_resource_utilization(node)
        return ResourceUtilization(
            cpu_utilization=util["cpu_utilization"],
            memory_utilization=util["memory_utilization"],
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to get node health: {str(e)}"
        )


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
