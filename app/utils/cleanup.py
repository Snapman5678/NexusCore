import logging
from typing import Optional
from .redis_client import RedisClient
from ..models.node import NodeStatus
from ..core.node_manager import NodeManager

logger = logging.getLogger(__name__)


class CleanupManager:
    def __init__(self, redis_client: Optional[RedisClient] = None):
        self.redis_client = redis_client or RedisClient.get_instance()
        self.node_manager = NodeManager(redis_client=self.redis_client)

    def cleanup_node(self, node_id: str) -> bool:
        """Clean up node data and related resources"""
        try:
            # Get node's pods
            node_pods = self.redis_client.get_node_pods(node_id)

            # Clean up pods
            for pod in node_pods:
                self.redis_client.delete_pod(pod.id)
                logger.info(f"Cleaned up pod {pod.id} from node {node_id}")

            # Remove node from Redis
            node = self.node_manager.get_node(node_id)
            if node:
                node.status = NodeStatus.OFFLINE
                self.redis_client.store_node(node)
                logger.info(f"Node {node_id} marked as offline")

            return True
        except Exception as e:
            logger.error(f"Error cleaning up node {node_id}: {str(e)}")
            return False

    def cleanup_stale_resources(self):
        """Clean up stale resources and offline nodes"""
        try:
            # Clean up offline nodes' resources
            nodes = self.node_manager.get_all_nodes()
            for node in nodes:
                if node.status == NodeStatus.OFFLINE:
                    self.cleanup_node(node.id)

            logger.info("Completed stale resource cleanup")
        except Exception as e:
            logger.error(f"Error during stale resource cleanup: {str(e)}")
