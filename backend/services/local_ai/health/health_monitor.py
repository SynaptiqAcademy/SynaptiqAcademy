"""System health monitor — CPU, RAM, GPU, disk, temperature."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("synaptiq.local_ai.health")


@dataclass
class SystemResourceHealth:
    cpu_pct: float = 0.0
    ram_used_gb: float = 0.0
    ram_total_gb: float = 0.0
    ram_pct: float = 0.0
    gpu_util_pct: float = 0.0
    gpu_memory_used_gb: float = 0.0
    gpu_memory_total_gb: float = 0.0
    gpu_available: bool = False
    gpu_name: str = ""
    disk_used_gb: float = 0.0
    disk_total_gb: float = 0.0
    disk_pct: float = 0.0
    temperature_celsius: float = -1.0  # -1 = unavailable

    def to_dict(self) -> dict:
        return {
            "cpu_pct": round(self.cpu_pct, 1),
            "ram": {
                "used_gb": round(self.ram_used_gb, 2),
                "total_gb": round(self.ram_total_gb, 2),
                "pct": round(self.ram_pct, 1),
            },
            "gpu": {
                "available": self.gpu_available,
                "name": self.gpu_name,
                "util_pct": round(self.gpu_util_pct, 1),
                "memory_used_gb": round(self.gpu_memory_used_gb, 2),
                "memory_total_gb": round(self.gpu_memory_total_gb, 2),
            },
            "disk": {
                "used_gb": round(self.disk_used_gb, 2),
                "total_gb": round(self.disk_total_gb, 2),
                "pct": round(self.disk_pct, 1),
            },
            "temperature_celsius": self.temperature_celsius,
        }


class HealthMonitor:
    """Collects system resource metrics using psutil (if available)."""

    async def get_system_health(self) -> SystemResourceHealth:
        try:
            import psutil
        except ImportError:
            logger.debug("psutil not installed — system health unavailable")
            return SystemResourceHealth()

        health = SystemResourceHealth()

        try:
            health.cpu_pct = psutil.cpu_percent(interval=0.1)
        except Exception:
            pass

        try:
            vm = psutil.virtual_memory()
            gb = 1024 ** 3
            health.ram_used_gb = vm.used / gb
            health.ram_total_gb = vm.total / gb
            health.ram_pct = vm.percent
        except Exception:
            pass

        try:
            disk = psutil.disk_usage("/")
            gb = 1024 ** 3
            health.disk_used_gb = disk.used / gb
            health.disk_total_gb = disk.total / gb
            health.disk_pct = disk.percent
        except Exception:
            pass

        try:
            temps = psutil.sensors_temperatures() if hasattr(psutil, "sensors_temperatures") else {}
            for sensor_list in (temps or {}).values():
                for reading in sensor_list:
                    if reading.current > 0:
                        health.temperature_celsius = reading.current
                        break
                if health.temperature_celsius > 0:
                    break
        except Exception:
            pass

        # GPU via pynvml (NVIDIA) — optional
        health = self._collect_gpu(health)

        return health

    def _collect_gpu(self, health: SystemResourceHealth) -> SystemResourceHealth:
        try:
            import pynvml
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            mem = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            name = pynvml.nvmlDeviceGetName(handle)
            gb = 1024 ** 3
            health.gpu_available = True
            health.gpu_name = name if isinstance(name, str) else name.decode("utf-8")
            health.gpu_memory_used_gb = mem.used / gb
            health.gpu_memory_total_gb = mem.total / gb
            health.gpu_util_pct = float(util.gpu)
        except Exception:
            pass
        return health
