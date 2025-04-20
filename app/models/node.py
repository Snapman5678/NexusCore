"""
Node Model Module

Defines data models for cluster nodes and their resources.
Represents compute units that can run pods.

Key Features:
- Node status tracking
- Resource capacity management
- Network information
- Heartbeat tracking
"""

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
    """
    Represents a compute node in the cluster.
    
    Contains resource information, network details, and status.
    Tracks heartbeats and current state.
    """
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    hostname: str
    ip_address: str
    status: NodeStatus = NodeStatus.OFFLINE
    resources: NodeResources
    last_heartbeat: Optional[datetime] = None


class NodeRegistration(BaseModel):
    cpu_count: int
    memory_mb: Optional[int] = None
