from __future__ import annotations

import platform
from dataclasses import dataclass

import psutil


@dataclass(frozen=True)
class HardwareProfile:
    name: str
    cpu_name: str
    cpu_cores: int
    ram_gb: float
    gpu_name: str
    whisper_model: str
    embedding_selection: str
    embedding_model: str
    embedding_batch_size: int
    low_memory_recommended: bool
    model_isolation_recommended: bool


class HardwareProfileDetector:
    def detect(self) -> HardwareProfile:
        ram_gb = psutil.virtual_memory().total / (1024**3)
        cpu_name = platform.processor() or platform.machine() or "Unknown CPU"
        cpu_cores = psutil.cpu_count(logical=True) or 1
        gpu_name = self._gpu_name()
        if ram_gb < 12:
            return HardwareProfile(
                name="Starter",
                cpu_name=cpu_name,
                cpu_cores=cpu_cores,
                ram_gb=ram_gb,
                gpu_name=gpu_name,
                whisper_model="tiny",
                embedding_selection="small",
                embedding_model="BAAI/bge-small-en-v1.5",
                embedding_batch_size=4,
                low_memory_recommended=True,
                model_isolation_recommended=True,
            )
        if ram_gb < 24:
            return HardwareProfile(
                name="Standard",
                cpu_name=cpu_name,
                cpu_cores=cpu_cores,
                ram_gb=ram_gb,
                gpu_name=gpu_name,
                whisper_model="small",
                embedding_selection="base",
                embedding_model="BAAI/bge-base-en-v1.5",
                embedding_batch_size=8,
                low_memory_recommended=False,
                model_isolation_recommended=True,
            )
        if ram_gb < 48:
            return HardwareProfile(
                name="Advanced",
                cpu_name=cpu_name,
                cpu_cores=cpu_cores,
                ram_gb=ram_gb,
                gpu_name=gpu_name,
                whisper_model="medium",
                embedding_selection="large",
                embedding_model="BAAI/bge-large-en-v1.5",
                embedding_batch_size=16,
                low_memory_recommended=False,
                model_isolation_recommended=False,
            )
        return HardwareProfile(
            name="Workstation",
            cpu_name=cpu_name,
            cpu_cores=cpu_cores,
            ram_gb=ram_gb,
            gpu_name=gpu_name,
            whisper_model="large",
            embedding_selection="large",
            embedding_model="BAAI/bge-large-en-v1.5",
            embedding_batch_size=32,
            low_memory_recommended=False,
            model_isolation_recommended=False,
        )

    def _gpu_name(self) -> str:
        try:
            import torch

            if torch.cuda.is_available():
                return str(torch.cuda.get_device_name(0))
        except Exception:
            pass
        return "No CUDA GPU detected"
