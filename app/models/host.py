"""
Host Model Module

Defines data models for host system resources and limits.
Tracks available resources and usage limits for the host system.

Key Features:
- Resource capacity tracking
- Usage limit definitions
- Available resource monitoring
"""

from pydantic import BaseModel


class HostResource(BaseModel):
    """
    Represents host system resources and usage limits.
    
    Tracks CPU cores, memory, and usage limit percentages.
    Used for ensuring host system stability.
    """
    cpu_count: int
    memory_total: int  # In bytes
    memory_available: int  # In bytes
    cpu_limit_percent: float = 50.0  # Default CPU usage limit in percentage
    memory_limit_percent: float = 90.0  # Default memory usage limit in percentage


class AvailableResource(BaseModel):
    cpu_count: int
    memory_total: int  # In bytes
    memory_available: int  # In bytes
