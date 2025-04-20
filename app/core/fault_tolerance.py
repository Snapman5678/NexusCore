"""
Fault Tolerance Module

Handles detection and recovery from resource-related failures in the cluster.
Manages pod rescheduling when nodes fail or become resource constrained.

Key Features:
- Resource failure detection
- Node health assessment
- Pod rescheduling on failure
- Resource utilization tracking
"""

# Pod rescheduling on node failure

from typing import List
from ..models.node import Node, NodeStatus
from ..models.pod import Pod, PodStatus
from .node_manager import NodeManager
from ..utils.redis_client import RedisClient
import logging


class ResourceFailureHandler:
    """
    Handles resource-related failures and recovery in the cluster.
    
    Detects resource exhaustion, manages node failures, and handles
    pod rescheduling when nodes become unhealthy or fail.
    """
    
    def __init__(self):
        """Initialize failure handler with Redis client and node manager."""
        self.redis_client = RedisClient.get_instance()
        self.node_manager = NodeManager()

    def check_node_resource_health(self, node: Node) -> bool:
        """Check if node's resources are within healthy limits"""
        # Get all pods on this node
        node_pods = self.redis_client.get_node_pods(node.id)

        # Calculate total resource usage
        total_cpu_used = sum(pod.resources.cpu_cores for pod in node_pods)
        total_memory_used = sum(
            pod.resources.memory_mb * 1024 * 1024 for pod in node_pods
        )

        # Check if usage exceeds node capacity
        if total_cpu_used > node.resources.cpu_count:
            logging.error(
                f"Node {node.id} CPU overloaded: {total_cpu_used}/{node.resources.cpu_count}"
            )
            return False

        if total_memory_used > node.resources.memory_total:
            logging.error(
                f"Node {node.id} memory overloaded: {total_memory_used}/{node.resources.memory_total}"
            )
            return False

        return True

    def handle_resource_failure(self, node: Node) -> List[Pod]:
        """Handle resource overload by marking node as failed and returning affected pods"""
        affected_pods = self.redis_client.get_node_pods(node.id)

        # Mark node as offline
        self.node_manager.update_node_status(node.id, NodeStatus.OFFLINE)

        # Mark pods as failed
        for pod in affected_pods:
            pod.status = PodStatus.FAILED
            self.redis_client.store_pod(pod)

        return affected_pods

    def check_cluster_health(self) -> None:
        """Check overall cluster resource health"""
        nodes = self.node_manager.get_all_nodes()

        for node in nodes:
            if node.status == NodeStatus.ONLINE:
                if not self.check_node_resource_health(node):
                    affected_pods = self.handle_resource_failure(node)
                    logging.warning(
                        f"Resource failure on node {node.id}. {len(affected_pods)} pods affected."
                    )

    def get_node_resource_utilization(self, node: Node) -> dict:
        """Get current resource utilization for a node"""
        node_pods = self.redis_client.get_node_pods(node.id)

        total_cpu_used = sum(pod.resources.cpu_cores for pod in node_pods)
        total_memory_used = sum(
            pod.resources.memory_mb * 1024 * 1024 for pod in node_pods
        )

        return {
            "cpu_utilization": (total_cpu_used / node.resources.cpu_count) * 100,
            "memory_utilization": (total_memory_used / node.resources.memory_total)
            * 100,
        }