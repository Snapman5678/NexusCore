from fastapi import APIRouter, HTTPException
from typing import List, Optional
from ..models.node import Node, NodeRegistration, NodeResources, NodeStatus
from ..models.pod import Pod
from ..core.node_manager import NodeManager
from pydantic import BaseModel
from ..utils.cleanup import CleanupManager

router = APIRouter()
node_manager = NodeManager()
cleanup_manager = CleanupManager()


class ContainerCreationRequest(BaseModel):
    cpu_count: int
    memory_mb: Optional[int] = None


@router.post("/", response_model=Node, status_code=201)
async def register_node(registration: NodeRegistration):
    """Register a new node with the cluster by creating a Docker container"""
    try:
        # Create the node container
        result = node_manager.create_node_container(
            cpu_count=registration.cpu_count,
            memory_mb=getattr(registration, "memory_mb", None),
        )
        return result["node"]
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to register node: {str(e)}"
        )


@router.get("/", response_model=List[Node])
async def list_nodes():
    """List all registered nodes"""
    try:
        nodes = node_manager.get_all_nodes()
        return nodes
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve nodes: {str(e)}"
        )


@router.get("/{node_id}", response_model=Node)
async def get_node(node_id: str):
    """Get details of a specific node"""
    node = node_manager.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    return node


@router.put("/{node_id}/status", response_model=Node)
async def update_node_status(node_id: str, status: NodeStatus):
    """Update a node's status"""
    updated_node = node_manager.update_node_status(node_id, status)
    if not updated_node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    return updated_node


@router.put("/{node_id}/resources", response_model=Node)
async def update_node_resources(node_id: str, resources: NodeResources):
    """Update a node's resource metrics"""
    # Get allocated resources first
    allocated = node_manager.redis_client.get_allocated_resources(node_id)
    if allocated:
        # Respect the originally allocated CPU count
        resources.cpu_count = allocated.get("cpu_count", resources.cpu_count)
        # Respect the originally allocated total memory
        resources.memory_total = allocated.get("memory_total", resources.memory_total)
        # Ensure available memory doesn't exceed the total allocation
        if resources.memory_available > resources.memory_total:
            resources.memory_available = resources.memory_total
    
    updated_node = node_manager.update_node_resources(node_id, resources)
    if not updated_node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    return updated_node


@router.post("/{node_id}/shutdown")
async def shutdown_node(node_id: str):
    """Handle graceful node shutdown"""
    try:
        if cleanup_manager.cleanup_node(node_id):
            return {"message": f"Node {node_id} shutdown handled successfully"}
        else:
            raise HTTPException(
                status_code=500, detail="Failed to handle node shutdown"
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error during node shutdown: {str(e)}"
        )


@router.post("/{node_id}/stop")
async def stop_node(node_id: str):
    """Stop a node's container"""
    try:
        if node_manager.stop_node(node_id):
            return {"message": f"Node {node_id} stopped successfully"}
        raise HTTPException(
            status_code=404, detail=f"Node {node_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error stopping node: {str(e)}"
        )


@router.post("/{node_id}/restart")
async def restart_node(node_id: str):
    """Restart a node's container"""
    try:
        if node_manager.restart_node(node_id):
            return {"message": f"Node {node_id} restarted successfully"}
        raise HTTPException(
            status_code=404, detail=f"Node {node_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error restarting node: {str(e)}"
        )


@router.delete("/{node_id}")
async def delete_node(node_id: str):
    """Delete a node and its container"""
    try:
        if node_manager.delete_node(node_id):
            return {"message": f"Node {node_id} deleted successfully"}
        raise HTTPException(
            status_code=404, detail=f"Node {node_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error deleting node: {str(e)}"
        )


@router.get("/{node_id}/pods", response_model=List[Pod])
async def list_node_pods(node_id: str):
    """List all pods running on a specific node"""
    node = node_manager.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    
    pods = node_manager.redis_client.get_node_pods(node_id)
    return pods


@router.get("/{node_id}/resources")
async def get_node_available_resources(node_id: str):
    """Get available resources on a specific node"""
    node = node_manager.get_node(node_id)
    if not node:
        raise HTTPException(status_code=404, detail=f"Node {node_id} not found")
    
    # Get all pods on this node to calculate used resources
    pods = node_manager.redis_client.get_node_pods(node_id)
    
    # Calculate used resources
    used_cpu = sum(pod.resources.cpu_cores for pod in pods)
    used_memory = sum(pod.resources.memory_mb * 1024 * 1024 for pod in pods)
    
    # Correctly calculate available resources based on the node's actual resources
    available_memory = node.resources.memory_total - used_memory

    available_resources = {
        "cpu_available": node.resources.cpu_count - used_cpu,
        "memory_available": available_memory,
        "total_cpu": node.resources.cpu_count,
        "total_memory": node.resources.memory_total,
        "used_cpu": used_cpu,
        "used_memory": used_memory,
        "cpu_utilization_percent": (used_cpu / node.resources.cpu_count * 100) if node.resources.cpu_count > 0 else 0,
        "memory_utilization_percent": (used_memory / node.resources.memory_total * 100) if node.resources.memory_total > 0 else 0
    }
    
    return available_resources
