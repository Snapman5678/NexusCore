"""
Node Manager Module

This module handles node lifecycle management including creation, deletion, 
status updates and resource management. It integrates with Docker for container 
management and Redis for state persistence.

Key Features:
- Node creation and deletion
- Resource tracking and updates
- Container lifecycle management
- Status management
"""

from datetime import datetime
from typing import List, Optional, Dict
from ..models.node import Node, NodeResources, NodeStatus
from ..utils.redis_client import RedisClient
from ..utils.docker_utils import DockerNodeManager


class NodeManager:
    """
    Manages node lifecycle and resources in the cluster.
    
    Handles node registration, status updates, resource tracking,
    and container management through Docker integration.
    
    Attributes:
        redis_client: Redis client for state persistence
        docker_manager: Docker client for container management
    """
    
    def __init__(self, redis_client=None, docker_manager=None):
        """
        Initialize NodeManager with optional Redis and Docker clients.
        
        Args:
            redis_client: Optional RedisClient instance
            docker_manager: Optional DockerNodeManager instance
        """
        self.redis_client = redis_client or RedisClient.get_instance()
        self.docker_manager = docker_manager or DockerNodeManager()

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by its ID"""
        return self.redis_client.get_node(node_id)

    def get_all_nodes(self) -> List[Node]:
        """Get all registered nodes"""
        return self.redis_client.get_all_nodes()

    def update_node_status(self, node_id: str, status: NodeStatus) -> Optional[Node]:
        """Update a node's status"""
        node = self.get_node(node_id)
        if not node:
            return None
        node.status = status
        self.redis_client.store_node(node)
        return node

    def update_node_resources(
        self, node_id: str, resources: NodeResources
    ) -> Optional[Node]:
        """Update a node's resources"""
        node = self.get_node(node_id)
        if not node:
            return None
            
        # Get the originally allocated resources to maintain the limits
        allocated = self.redis_client.get_allocated_resources(node_id)
        if allocated:
            # Preserve the originally allocated CPU count
            resources.cpu_count = allocated.get("cpu_count", resources.cpu_count)
            # Preserve the total memory allocation
            resources.memory_total = allocated.get("memory_total", resources.memory_total)
            # Ensure available memory doesn't exceed the total allocation
            if resources.memory_available > resources.memory_total:
                resources.memory_available = resources.memory_total
                
        node.resources = resources
        node.last_heartbeat = datetime.now()
        self.redis_client.store_node(node)
        return node

    def create_node_container(
        self, cpu_count: int, memory_mb: Optional[int] = None
    ) -> Dict:
        """Create a new node as a Docker container"""
        try:
            # Create the container
            container_info = self.docker_manager.create_node_container(
                cpu_count, memory_mb
            )

            # Convert MB to bytes for consistent storage
            memory_bytes = memory_mb * 1024 * 1024 if memory_mb else 0
            
            # Create and store the node object
            node = Node(
                id=container_info["container_id"],  
                hostname=container_info["hostname"],
                ip_address=container_info["ip_address"],
                resources=NodeResources(
                    cpu_count=cpu_count,
                    memory_total=memory_bytes,
                    memory_available=memory_bytes,
                ),
                status=NodeStatus.ONLINE,
            )
            
            # Store the originally allocated resources separately to prevent overwriting
            self.redis_client.store_allocated_resources(node.id, {
                "cpu_count": cpu_count,
                "memory_total": memory_bytes,
                "memory_available": memory_bytes
            })
            
            self.redis_client.store_node(node)

            return {"node": node, "container": container_info}
        except Exception as e:
            print(f"Failed to create node container: {str(e)}")
            raise

    def stop_node(self, node_id: str) -> bool:
        """Stop a node's container"""
        node = self.get_node(node_id)
        if not node:
            return False
        # Stop the container
        if self.docker_manager.stop_node_container(node.id):
            # Update node status
            node.status = NodeStatus.OFFLINE
            self.redis_client.store_node(node)
            return True
        return False

    def restart_node(self, node_id: str) -> bool:
        """Restart a node's container"""
        node = self.get_node(node_id)
        if not node:
            return False
        # Restart the container
        if self.docker_manager.restart_node_container(node.id):
            # Update node status
            node.status = NodeStatus.ONLINE
            self.redis_client.store_node(node)
            return True
        return False

    def delete_node(self, node_id: str) -> bool:
        """Delete a node and its container"""
        node = self.get_node(node_id)
        if not node:
            return False
        
        # First delete the container
        if not self.docker_manager.delete_node_container(node.id):
            return False
            
        # Clean up any pods associated with this node
        node_pods = self.redis_client.get_node_pods(node_id)
        for pod in node_pods:
            self.redis_client.delete_pod(pod.id)
            
        # Remove node from Redis
        self.redis_client.delete(f"node:{node_id}")
        self.redis_client.get_connection().srem("nodes", node_id)
            
        return True
