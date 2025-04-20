"""
Health Monitor Module

Provides continuous monitoring of cluster health including node heartbeats,
resource utilization, and overall cluster status.

Key Features:
- Node heartbeat monitoring
- Resource utilization tracking
- Health status management
- Failure detection
"""

import time
import threading
import logging
from datetime import datetime
from typing import Set
from ..models.node import NodeStatus
from ..utils.redis_client import RedisClient
from .node_manager import NodeManager


class HealthMonitorService:
    """
    Service for monitoring cluster and node health.
    
    Tracks node heartbeats, resource utilization, and overall cluster health.
    Detects node failures and resource exhaustion conditions.
    
    Attributes:
        check_interval: Time between health checks in seconds
        failed_nodes: Set of node IDs that have failed
    """
    
    def __init__(self, check_interval=60):
        """
        Initialize health monitor service.
        
        Args:
            check_interval: Seconds between health checks (default: 60)
        """
        self.check_interval = check_interval
        self.redis_client = RedisClient.get_instance()
        self.node_manager = NodeManager(redis_client=self.redis_client)
        self.lock = threading.Lock()
        self.failed_nodes: Set[str] = set()
        self.is_running = False

    def check_nodes_health(self):
        """Check health of all nodes based on heartbeats"""
        current_time = datetime.now()
        nodes = self.node_manager.get_all_nodes()

        for node in nodes:
            if node.status != NodeStatus.OFFLINE and node.last_heartbeat:
                # If heartbeat is older than 5 minutes, mark as offline
                time_diff = (current_time - node.last_heartbeat).total_seconds()
                if time_diff > 300:  # 5 minutes
                    print(f"Node {node.id} missed heartbeat - marking as OFFLINE")
                    self.node_manager.update_node_status(node.id, NodeStatus.OFFLINE)

                    with self.lock:
                        self.failed_nodes.add(node.id)

    def check_node_resource_health(self, node) -> bool:
        """Check if node resources are healthy and within limits"""
        try:
            # Get current host resource limits
            host_resources = self.redis_client.get_connection().get("host:resources")
            if not host_resources:
                return True  # If no limits set, assume healthy

            from ..models.host import HostResource

            host_limits = HostResource.model_validate_json(host_resources)

            # Get node's current pods and calculate resource usage
            pods = self.redis_client.get_node_pods(node.id)
            total_cpu_used = sum(pod.resources.cpu_cores for pod in pods)
            total_memory_mb_used = sum(pod.resources.memory_mb for pod in pods)

            # Calculate utilization percentages
            cpu_utilization = (total_cpu_used / node.resources.cpu_count) * 100
            memory_utilization = (
                total_memory_mb_used * 1024 * 1024 / node.resources.memory_total
            ) * 100

            # Check against limits
            if cpu_utilization > host_limits.cpu_limit_percent:
                logging.warning(
                    f"Node {node.id} CPU utilization ({cpu_utilization:.1f}%) exceeds limit ({host_limits.cpu_limit_percent}%)"
                )
                return False

            if memory_utilization > host_limits.memory_limit_percent:
                logging.warning(
                    f"Node {node.id} memory utilization ({memory_utilization:.1f}%) exceeds limit ({host_limits.memory_limit_percent}%)"
                )
                return False

            return True
        except Exception as e:
            logging.error(f"Error checking node health: {str(e)}")
            return False

    def check_cluster_health(self):
        """Check overall cluster health including nodes and their resources"""
        try:
            self.check_nodes_health()
            nodes = self.node_manager.get_all_nodes()

            # Calculate cluster-wide metrics
            online_nodes = [node for node in nodes if node.status == NodeStatus.ONLINE]
            if not online_nodes:
                logging.warning("No online nodes found in cluster")
                return

            for node in online_nodes:
                if not self.check_node_resource_health(node):
                    logging.warning(f"Node {node.id} has resource issues")
        except Exception as e:
            logging.error(f"Error checking cluster health: {str(e)}")

    def is_monitoring_active(self) -> bool:
        """Check if monitoring is active"""
        return self.is_running

    def start_monitoring(self):
        """Start the health monitoring process"""
        self.is_running = True
        print("Health monitoring service started")
        while self.is_running:
            try:
                self.check_nodes_health()
            except Exception as e:
                print(f"Error in health monitoring: {str(e)}")
            time.sleep(self.check_interval)

    def stop_monitoring(self):
        """Stop the health monitoring process"""
        self.is_running = False
