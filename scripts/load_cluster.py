"""
Load Testing Script for NexusCore Cluster

Creates multiple nodes and pods to test cluster capacity and scheduling.
Monitors resource allocation and scheduling decisions.
"""

import sys
import os
import time
import random
import logging
import requests
import json
import signal
from typing import List, Dict

# Add project root to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('cluster_load_test.log')
    ]
)

API_BASE_URL = "http://localhost:8000"

# Global variable to track created nodes for cleanup
created_nodes = []

def create_node(cpu_count: int, memory_mb: int) -> Dict:
    """Create a new node with specified resources"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/nodes",
            json={"cpu_count": cpu_count, "memory_mb": memory_mb}
        )
        if response.status_code == 201:
            node_data = response.json()
            logging.info(f"Created node {node_data['id']} with {cpu_count} CPUs and {memory_mb}MB memory")
            return node_data
        else:
            logging.error(f"Failed to create node: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error creating node: {str(e)}")
        return None

def create_pod(name: str, cpu_cores: int, memory_mb: int) -> Dict:
    """Create a new pod with specified resource requirements"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/pods",
            json={
                "name": name,
                "resources": {
                    "cpu_cores": cpu_cores,
                    "memory_mb": memory_mb
                }
            }
        )
        if response.status_code == 201:
            pod_data = response.json()
            logging.info(f"Created pod {pod_data['id']} with {cpu_cores} cores and {memory_mb}MB memory")
            return pod_data
        else:
            logging.error(f"Failed to create pod: {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error creating pod: {str(e)}")
        return None

def delete_all_nodes() -> None:
    """Delete all nodes in the cluster"""
    try:
        # Using the new API endpoint to delete all nodes at once
        response = requests.delete(f"{API_BASE_URL}/nodes")
        if response.status_code == 200:
            result = response.json()
            logging.info(f"Bulk node deletion result: {result['message']}")
        else:
            logging.error(f"Failed to delete all nodes: {response.text}")
            
            # Fallback to individual node deletion if bulk deletion fails
            node_list = requests.get(f"{API_BASE_URL}/nodes").json()
            for node in node_list:
                node_id = node['id']
                shutdown_response = requests.post(f"{API_BASE_URL}/nodes/{node_id}/shutdown")
                delete_response = requests.delete(f"{API_BASE_URL}/nodes/{node_id}")
                if delete_response.status_code == 200:
                    logging.info(f"Deleted node {node_id}")
                else:
                    logging.error(f"Failed to delete node {node_id}: {delete_response.text}")
    except Exception as e:
        logging.error(f"Error during node deletion: {str(e)}")

def get_cluster_health() -> Dict:
    """Get current cluster health metrics"""
    try:
        response = requests.get(f"{API_BASE_URL}/health/cluster")
        if response.status_code == 200:
            return response.json()
        return None
    except Exception as e:
        logging.error(f"Error getting cluster health: {str(e)}")
        return None

def signal_handler(sig, frame):
    """Handle Ctrl+C by cleaning up resources before exit"""
    logging.info("\nCtrl+C detected! Cleaning up resources before exit...")
    delete_all_nodes()
    logging.info("Cleanup complete. Exiting.")
    sys.exit(0)

def main():
    # Register the signal handler for Ctrl+C
    signal.signal(signal.SIGINT, signal_handler)
    
    # Node configurations
    node_configs = [
        {"cpu": 2, "memory": 2048},  # Small nodes
        {"cpu": 4, "memory": 4096},  # Medium nodes
        {"cpu": 8, "memory": 8192},  # Large nodes
    ]

    # Pod configurations
    pod_configs = [
        {"cpu": 1, "memory": 512},   # Small pods
        {"cpu": 2, "memory": 1024},  # Medium pods
        {"cpu": 4, "memory": 2048},  # Large pods
    ]

    # Create nodes
    global created_nodes
    logging.info("Starting node creation...")
    for i in range(5):
        config = random.choice(node_configs)
        node = create_node(config["cpu"], config["memory"])
        if node:
            created_nodes.append(node)
        time.sleep(2)  # Delay between node creation

    logging.info(f"Created {len(created_nodes)} nodes")
    time.sleep(10)  # Wait for nodes to initialize

    # Create pods
    pods = []
    logging.info("Starting pod creation...")
    for i in range(10):  # Create more pods than nodes to test scheduling
        config = random.choice(pod_configs)
        pod = create_pod(
            f"test-pod-{i}",
            config["cpu"],
            config["memory"]
        )
        if pod:
            pods.append(pod)
        time.sleep(1)  # Delay between pod creation

    logging.info(f"Created {len(pods)} pods")

    # Monitor cluster health periodically until Ctrl+C
    logging.info("Monitoring cluster health. Press Ctrl+C to terminate and clean up.")
    try:
        while True:
            health = get_cluster_health()
            if health:
                logging.info("\nCurrent Cluster Health:")
                logging.info(f"Total Nodes: {health['total_nodes']}")
                logging.info(f"Online Nodes: {health['online_nodes']}")
                logging.info(f"Average CPU Utilization: {health['average_cpu_utilization']:.1f}%")
                logging.info(f"Average Memory Utilization: {health['average_memory_utilization']:.1f}%")
                
                # Save updated metrics
                with open('cluster_metrics.json', 'w') as f:
                    json.dump(health, f, indent=2)
            
            # Wait before checking again
            time.sleep(30)
    except KeyboardInterrupt:
        # This will be caught by our signal handler
        pass

if __name__ == "__main__":
    main()
