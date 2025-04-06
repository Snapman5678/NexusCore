from pydantic import BaseModel


class HostResource(BaseModel):
    cpu_count: int
    memory_total: int  # In bytes
    memory_available: int  # In bytes
    cpu_limit_percent: float = 50.0  # Default CPU usage limit in percentage
    memory_limit_percent: float = 90.0  # Default memory usage limit in percentage


class AvailableResource(BaseModel):
    cpu_count: int
    memory_total: int  # In bytes
    memory_available: int  # In bytes
