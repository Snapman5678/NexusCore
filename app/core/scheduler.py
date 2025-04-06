# Best-Fit scheduler

from typing import Optional, List
from ..models.node import Node, NodeStatus
from ..models.pod import Pod
from ..utils.redis_client import RedisClient
from .node_manager import NodeManager


class Scheduler:
    def __init__(self):
        self.redis_client = RedisClient.get_instance()
        self.node_manager = NodeManager(redis_client=self.redis_client)

    def get_available_nodes(self) -> List[Node]:
        """Get all online nodes"""
        all_nodes = self.node_manager.get_all_nodes()
        return [node for node in all_nodes if node.status == NodeStatus.ONLINE]

    def can_node_fit_pod(self, node: Node, pod: Pod) -> bool:
        """Check if a node has enough resources for a pod"""
        # Get existing pods on this node
        node_pods = self.redis_client.get_node_pods(node.id)

        # Calculate used resources
        used_cpu = sum(p.resources.cpu_cores for p in node_pods)
        used_memory = sum(p.resources.memory_mb * 1024 * 1024 for p in node_pods)

        # Check if node can support this pod
        available_cpu = node.resources.cpu_count - used_cpu
        available_memory = node.resources.memory_available

        return (
            available_cpu >= pod.resources.cpu_cores
            and available_memory >= pod.resources.memory_mb * 1024 * 1024
        )

    def schedule_pod(self, pod: Pod) -> Optional[Node]:
        """Schedule a pod using Best-Fit algorithm"""
        available_nodes = self.get_available_nodes()
        if not available_nodes:
            return None

        # Find the node with the least remaining resources that can fit the pod
        best_fit_node = None
        minimum_remaining_cpu = float("inf")

        for node in available_nodes:
            if not self.can_node_fit_pod(node, pod):
                continue

            # Calculate remaining CPU after placing this pod
            node_pods = self.redis_client.get_node_pods(node.id)
            used_cpu = sum(p.resources.cpu_cores for p in node_pods)
            remaining_cpu = (
                node.resources.cpu_count - used_cpu - pod.resources.cpu_cores
            )

            if 0 <= remaining_cpu < minimum_remaining_cpu:
                minimum_remaining_cpu = remaining_cpu
                best_fit_node = node

        return best_fit_node
