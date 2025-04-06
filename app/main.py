from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import logging
from .api import nodes, pods, health, host
from .core.health_monitor import HealthMonitorService
from .utils.redis_client import RedisHostResourceMonitor
from .utils.cleanup import CleanupManager
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    health_monitor = HealthMonitorService()
    host_monitor = RedisHostResourceMonitor()
    cleanup_manager = CleanupManager()

    # Start background tasks
    host_monitor_task = asyncio.create_task(run_host_monitor(host_monitor))
    health_monitor_task = asyncio.create_task(run_health_monitor(health_monitor))
    logging.info("Started resource monitoring services")

    yield

    # Shutdown: Clean up resources and cancel background tasks
    logging.info("Starting cleanup process...")
    cleanup_manager.cleanup_stale_resources()
    host_monitor_task.cancel()
    health_monitor_task.cancel()
    try:
        await host_monitor_task
        await health_monitor_task
    except asyncio.CancelledError:
        pass
    logging.info("Cleanup completed")


app = FastAPI(
    title="NexusCore API",
    description="Resource monitoring and management system for distributed environments",
    version="1.0.0",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(nodes.router, prefix="/nodes", tags=["nodes"])
app.include_router(pods.router, prefix="/pods", tags=["pods"])
app.include_router(health.router, prefix="/health", tags=["health"])
app.include_router(host.router, prefix="/host", tags=["host"])

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


async def run_host_monitor(host_monitor: RedisHostResourceMonitor):
    """Run host resource monitoring in the background"""
    while True:
        try:
            host_monitor.update_host_resources()
            await asyncio.sleep(30)  # Update every 30 seconds
        except Exception as e:
            logging.error(f"Error in host monitor: {str(e)}")
            await asyncio.sleep(5)


async def run_health_monitor(health_monitor: HealthMonitorService):
    """Run cluster health monitoring in the background"""
    while True:
        try:
            health_monitor.check_cluster_health()
            await asyncio.sleep(60)  # Check every minute
        except Exception as e:
            logging.error(f"Error in health monitor: {str(e)}")
            await asyncio.sleep(5)


@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "NexusCore API",
        "version": "1.0.0",
        "description": "Resource monitoring and management system",
    }
