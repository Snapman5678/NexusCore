import time
import os
import requests
import psutil
import logging
import signal
import sys


class HeartbeatClient:
    def __init__(self, node_id: str, api_url: str = "http://localhost:8000"):
        self.node_id = node_id
        self.api_url = api_url
        self.is_running = True
        self.container_id = self._get_container_id()  # Get container ID

        # Setup logging
        logging.basicConfig(
            level=os.environ.get("LOG_LEVEL", "INFO"),
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger("HeartbeatClient")
        self.logger.info(
            f"Initializing heartbeat client (Node: {node_id}, Container: {self.container_id})"
        )

    def _get_container_id(self) -> str:
        """Get the current container ID (if running in Docker)"""
        try:
            # Read container ID from /proc/self/cgroup (Linux)
            with open("/proc/self/cgroup", "r") as f:
                for line in f:
                    if "docker" in line:
                        return line.strip().split("/")[-1]
        except Exception:
            pass

        # Fallback to HOSTNAME or node_id if not in Docker
        return os.environ.get("HOSTNAME", self.node_id)

    def collect_metrics(self) -> dict:
        """Collect current system metrics"""
        metrics = {
            "resources": {
                "cpu_count": psutil.cpu_count(),
                "memory_total": psutil.virtual_memory().total,
                "memory_available": psutil.virtual_memory().available,
            },
            "status": "online",
            "container_id": self.container_id,  # Include container ID in metrics
        }
        self.logger.debug(f"Collected metrics: {metrics}")
        return metrics

    def send_heartbeat(self) -> bool:
        """Send a heartbeat with current metrics to the API"""
        try:
            metrics = self.collect_metrics()
            self.logger.debug(
                f"Sending heartbeat to {self.api_url}/health/heartbeat/{self.container_id}"
            )

            response = requests.post(
                f"{self.api_url}/health/heartbeat/{self.container_id}",  # Use container_id in URL
                json=metrics,
                timeout=5,
            )

            if response.status_code == 200:
                self.logger.info(
                    f"Heartbeat sent successfully (Container: {self.container_id})"
                )
                return True
            else:
                self.logger.error(
                    f"Failed to send heartbeat: Status {response.status_code} - {response.text}"
                )
                return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Network error sending heartbeat: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Unexpected error sending heartbeat: {str(e)}")
            return False

    def start_heartbeat_loop(self, interval: int = 30):
        """Start sending periodic heartbeats"""
        self.logger.info(f"Starting heartbeat loop with {interval}s interval")
        consecutive_failures = 0

        # Register signal handlers
        signal.signal(signal.SIGTERM, self._handle_shutdown)
        signal.signal(signal.SIGINT, self._handle_shutdown)

        while self.is_running:
            try:
                if self.send_heartbeat():
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    if consecutive_failures > 3:
                        self.logger.warning(
                            f"Multiple consecutive heartbeat failures: {consecutive_failures}"
                        )
                time.sleep(interval)
            except Exception as e:
                self.logger.error(f"Error in heartbeat loop: {str(e)}")
                time.sleep(5)

    def cleanup(self):
        """Cleanup resources before shutdown"""
        try:
            self.logger.info(f"Cleaning up resources for container {self.container_id}")
            response = requests.post(
                f"{self.api_url}/nodes/{self.container_id}/shutdown",  # Use container_id
                timeout=5,
            )
            if response.status_code == 200:
                self.logger.info(
                    f"Successfully cleaned up container {self.container_id}"
                )
            else:
                self.logger.error(f"Failed to cleanup: Status {response.status_code}")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {str(e)}")

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals"""
        self.logger.info(f"Received shutdown signal {signum}")
        self.stop()
        self.cleanup()
        sys.exit(0)

    def stop(self):
        """Stop the heartbeat loop"""
        self.logger.info("Stopping heartbeat client")
        self.is_running = False


def main():
    required_env_vars = ["NODE_ID", "API_URL"]
    missing_vars = [var for var in required_env_vars if not os.environ.get(var)]

    if missing_vars:
        print(
            f"Error: Missing required environment variables: {', '.join(missing_vars)}"
        )
        sys.exit(1)

    node_id = os.environ["NODE_ID"]
    api_url = os.environ["API_URL"]

    client = HeartbeatClient(node_id, api_url)
    try:
        client.start_heartbeat_loop()
    except KeyboardInterrupt:
        client.stop()
        client.cleanup()


if __name__ == "__main__":
    main()
