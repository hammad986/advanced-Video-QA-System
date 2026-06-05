from __future__ import annotations

from dataclasses import dataclass

import psutil

from desktop_app.embeddings.model_registry import EmbeddingModelRegistry


@dataclass(frozen=True)
class MemorySnapshot:
    current_ram_mb: float
    peak_ram_mb: float
    system_ram_gb: float
    loaded_models: int
    model_names: list[str]
    model_memory_estimate_mb: float
    pipeline_status: str


class MemoryMonitor:
    def __init__(self, model_registry: EmbeddingModelRegistry, *, pipeline_status: str = "Idle") -> None:
        self.model_registry = model_registry
        self.pipeline_status = pipeline_status
        self._process = psutil.Process()
        self._peak_ram_mb = self.current_ram_mb()

    def current_ram_mb(self) -> float:
        return self._process.memory_info().rss / (1024 * 1024)

    def snapshot(self) -> MemorySnapshot:
        current = self.current_ram_mb()
        self._peak_ram_mb = max(self._peak_ram_mb, current)
        model_names = self.model_registry.loaded_model_names()
        return MemorySnapshot(
            current_ram_mb=current,
            peak_ram_mb=self._peak_ram_mb,
            system_ram_gb=psutil.virtual_memory().total / (1024**3),
            loaded_models=len(model_names),
            model_names=model_names,
            model_memory_estimate_mb=self.model_registry.estimated_model_memory_mb(),
            pipeline_status=self.pipeline_status,
        )

    def set_pipeline_status(self, status: str) -> None:
        self.pipeline_status = status
