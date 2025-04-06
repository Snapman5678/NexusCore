import psutil
from ..models.host import HostResource


class HostResourceMonitor:
    def __init__(self):
        pass

    def collect_metrics(self) -> HostResource:
        """Collect system metrics using psutil"""
        return HostResource(
            cpu_count=psutil.cpu_count(),
            memory_total=psutil.virtual_memory().total,
            memory_available=psutil.virtual_memory().available,
        )

    def update_metrics(self) -> HostResource:
        """Collect metrics and return as HostResources object"""
        return self.collect_metrics()
