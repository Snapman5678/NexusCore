from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum
import uuid


class NodeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"


class NodeResources(BaseModel):
    cpu_count: int
    memory_total: int  # In bytes
    memory_available: int  # In bytes


class Node(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hostname: str
    ip_address: str
    status: NodeStatus = NodeStatus.OFFLINE
    resources: NodeResources
    last_heartbeat: Optional[datetime] = None


class NodeRegistration(BaseModel):
    cpu_count: int
    memory_mb: Optional[int] = None
