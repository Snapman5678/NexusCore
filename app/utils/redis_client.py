import redis
import time
import json
from datetime import datetime
from typing import Optional, List, Dict
from ..models.node import Node, NodeResources
from ..models.host import HostResource
from ..utils.host_client import HostResourceMonitor


class RedisClient:
    _instance = None
    _pool = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self, host="localhost", port=6379, db=0):
        if RedisClient._pool is None:
            RedisClient._pool = redis.ConnectionPool(host=host, port=port, db=db)
        self.redis = redis.Redis(connection_pool=RedisClient._pool)

    def get_connection(self):
        """Get the Redis connection"""
        return self.redis

    def store_node(self, node: Node):
        """Store node information in Redis"""
        node_key = f"node:{node.id}"
        self.redis.set(node_key, node.model_dump_json())
        self.redis.sadd("nodes", node.id)
        return True

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get node information from Redis"""
        node_key = f"node:{node_id}"
        node_data = self.redis.get(node_key)
        if node_data:
            return Node.model_validate_json(node_data)
        return None

    def get_all_nodes(self) -> List[Node]:
        """Get all nodes from Redis"""
        nodes = []
        node_ids = self.redis.smembers("nodes")
        for node_id in node_ids:
            node = self.get_node(node_id.decode())
            if node:
                nodes.append(node)
        return nodes

    def store_allocated_resources(self, node_id: str, resources: Dict):
        """Store the originally allocated resources for a node"""
        self.redis.set(f"node:{node_id}:allocated", json.dumps(resources))
        
    def get_allocated_resources(self, node_id: str) -> Optional[Dict]:
        """Get the originally allocated resources for a node"""
        data = self.redis.get(f"node:{node_id}:allocated")
        if data:
            return json.loads(data)
        return None

    def update_node_resources(self, node_id: str, resources: NodeResources):
        """Update node resources in Redis"""
        node = self.get_node(node_id)
        if node:
            # Get the originally allocated resources
            allocated = self.get_allocated_resources(node_id)
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
            self.store_node(node)
            return True
        return False

    def store_pod(self, pod):
        """Store pod information in Redis"""
        pod_key = f"pod:{pod.id}"
        self.redis.set(pod_key, pod.model_dump_json())
        self.redis.sadd("pods", pod.id)
        if pod.node_id:
            self.redis.sadd(f"node:{pod.node_id}:pods", pod.id)
        return True

    def get_pod(self, pod_id: str):
        """Get pod information from Redis"""
        pod_key = f"pod:{pod_id}"
        pod_data = self.redis.get(pod_key)
        if pod_data:
            from ..models.pod import Pod

            return Pod.model_validate_json(pod_data)
        return None

    def get_all_pods(self) -> list:
        """Get all pods from Redis"""
        pods = []
        pod_ids = self.redis.smembers("pods")
        for pod_id in pod_ids:
            pod = self.get_pod(pod_id.decode())
            if pod:
                pods.append(pod)
        return pods

    def get_node_pods(self, node_id: str) -> list:
        """Get all pods assigned to a specific node"""
        pods = []
        pod_ids = self.redis.smembers(f"node:{node_id}:pods")
        for pod_id in pod_ids:
            pod = self.get_pod(pod_id.decode())
            if pod:
                pods.append(pod)
        return pods

    def delete_pod(self, pod_id: str) -> bool:
        """Delete a pod from Redis"""
        pod = self.get_pod(pod_id)
        if not pod:
            return False
        if pod.node_id:
            self.redis.srem(f"node:{pod.node_id}:pods", pod_id)
        self.redis.srem("pods", pod_id)
        self.redis.delete(f"pod:{pod_id}")
        return True

    def delete(self, key: str) -> bool:
        """Delete a key from Redis"""
        return bool(self.redis.delete(key))


class RedisHostResourceMonitor:
    def __init__(
        self, redis_client: Optional[RedisClient] = None, update_interval: int = 30
    ):
        self.redis_client = redis_client or RedisClient.get_instance()
        self.host_resource_monitor = HostResourceMonitor()
        self.update_interval = update_interval
        self.is_running = False

    def update_host_resources(self):
        """Collect and store host resources in Redis"""
        metrics = self.host_resource_monitor.update_metrics()
        self.redis_client.get_connection().set(
            "host:resources", metrics.model_dump_json()
        )
        self.redis_client.get_connection().set("host:last_update", str(time.time()))
        return metrics

    def update_limits(self, cpu_limit: float, memory_limit: float):
        """Update CPU and memory usage limits"""
        resource_data = self.get_latest_resources()
        if resource_data:
            resource_data.cpu_limit_percent = cpu_limit
            resource_data.memory_limit_percent = memory_limit
            self.redis_client.get_connection().set(
                "host:resources", resource_data.model_dump_json()
            )

    def get_latest_resources(self) -> Optional[HostResource]:
        """Get the latest host resources from Redis"""
        resource_data = self.redis_client.get_connection().get("host:resources")
        if resource_data:
            return HostResource.model_validate_json(resource_data)
        return None

    def start_monitoring(self):
        """Start monitoring host resources"""
        self.is_running = True
        while self.is_running:
            self.update_host_resources()
            time.sleep(self.update_interval)

    def stop_monitoring(self):
        """Stop the monitoring process"""
        self.is_running = False
