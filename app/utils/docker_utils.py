"""
Docker Utils Module

Manages Docker container operations for simulated nodes.
Handles container lifecycle including creation, deletion, and resource limits.

Key Features:
- Container lifecycle management
- Resource constraint configuration
- Network management
- Container health monitoring
"""

# Node container management

import docker
import uuid
import time
from typing import Dict, Optional
import os


class DockerNodeManager:
    """
    Manages Docker containers that simulate cluster nodes.
    
    Handles container lifecycle operations and resource configurations.
    Ensures proper network setup and resource constraints.
    """
    def __init__(self):
        """Initialize Docker client"""
        self.client = docker.from_env()
        self.network_name = "nexuscore-network"
        self._ensure_network()

    def _ensure_network(self):
        """Make sure the NexusCore network exists"""
        networks = self.client.networks.list(names=[self.network_name])
        if not networks:
            self.client.networks.create(name=self.network_name, driver="bridge")

    def create_node_container(
        self, cpu_count: int, memory_mb: Optional[int] = None
    ) -> Dict:
        """Create a Docker container to simulate a node

        Args:
            cpu_count: Number of CPU cores to allocate
            memory_mb: Memory limit in MB (optional)
        """
        node_name = f"nexus-node-{str(uuid.uuid4())[:8]}"
        
        # Ensure proper resource constraints
        nano_cpus = int(cpu_count * 1e9)  # Convert CPU count to nano CPUs
        memory_bytes = memory_mb * 1024 * 1024 if memory_mb else None

        # Container configuration
        container_options = {
            "image": "nexuscore-node:latest",
            "name": node_name,
            "detach": True,
            "environment": {
                "NODE_CPU_COUNT": str(cpu_count),
                "NODE_ID": node_name,
                "API_URL": os.environ.get(
"NODE_API_URL", "http://host.docker.internal:8000"
),
                "PYTHONUNBUFFERED": "1",
                "LOG_LEVEL": "INFO",
            },
            "network": self.network_name,
            "nano_cpus": nano_cpus,  # Set CPU limit using nano CPUs
            "log_config": {
                "type": "json-file",
                "config": {"max-size": "10m", "max-file": "3"},
            }
        }

        # Set memory constraints if specified
        if memory_bytes:
            container_options["mem_limit"] = memory_bytes
            container_options["memswap_limit"] = memory_bytes  # Disable swap
            container_options["environment"]["NODE_MEMORY_MB"] = str(memory_mb)

        try:
            # Try to remove any existing container with the same name
            try:
                old_container = self.client.containers.get(node_name)
                old_container.remove(force=True)
            except:
                pass

            container = self.client.containers.run(**container_options)
            container.reload()

            # Wait briefly and check container is actually running
            time.sleep(2)
            container.reload()
            if container.status != "running":
                logs = container.logs().decode("utf-8")
                raise Exception(f"Container failed to start. Logs: {logs}")

            ip_address = container.attrs["NetworkSettings"]["Networks"][
                self.network_name
            ]["IPAddress"]

            print(f"Created node container {node_name} with IP {ip_address}")
            return {
                "container_id": container.id,
                "hostname": node_name,
                "ip_address": ip_address,
            }
        except Exception as e:
            print(f"Error creating container: {str(e)}")
            raise

    def stop_node_container(self, container_id: str) -> bool:
        """Stop a node container"""
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            return True
        except Exception as e:
            print(f"Error stopping container: {str(e)}")
            return False

    def restart_node_container(self, container_id: str) -> bool:
        """Restart a node container"""
        try:
            container = self.client.containers.get(container_id)
            container.restart()
            return True
        except Exception as e:
            print(f"Error restarting container: {str(e)}")
            return False

    def delete_node_container(self, container_id: str) -> bool:
        """Delete a node container"""
        try:
            container = self.client.containers.get(container_id)
            container.remove(force=True)
            return True
        except Exception as e:
            print(f"Error deleting container: {str(e)}")
            return False
