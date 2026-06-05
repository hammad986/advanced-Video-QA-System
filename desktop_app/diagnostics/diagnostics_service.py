from __future__ import annotations

import json
import platform
import time
from dataclasses import asdict, dataclass
from pathlib import Path

try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None  # type: ignore[assignment]

from desktop_app.providers.provider_health import ProviderHealthResult


@dataclass(frozen=True)
class DiagnosticsSnapshot:
    cpu_percent: float
    ram_total_mb: float
    ram_used_mb: float
    ram_percent: float
    gpu_summary: str
    worker_status: str
    provider_status: dict[str, str]
    queue_status: str
    platform_summary: str
    captured_at: float


class DiagnosticsService:
    def capture(
        self,
        *,
        provider_results: list[ProviderHealthResult] | None = None,
        worker_status: str = "Unknown",
        queue_status: str = "Unknown",
    ) -> DiagnosticsSnapshot:
        if psutil is not None:
            memory = psutil.virtual_memory()
            cpu_percent = float(psutil.cpu_percent(interval=0.0))
            ram_total_mb = float(memory.total / (1024 * 1024))
            ram_used_mb = float(memory.used / (1024 * 1024))
            ram_percent = float(memory.percent)
        else:
            cpu_percent = 0.0
            ram_total_mb = 0.0
            ram_used_mb = 0.0
            ram_percent = 0.0
        provider_status = {
            result.provider.value: result.status.value
            for result in (provider_results or [])
        }
        return DiagnosticsSnapshot(
            cpu_percent=cpu_percent,
            ram_total_mb=ram_total_mb,
            ram_used_mb=ram_used_mb,
            ram_percent=ram_percent,
            gpu_summary=self._gpu_summary(),
            worker_status=worker_status,
            provider_status=provider_status,
            queue_status=queue_status,
            platform_summary=f"{platform.system()} {platform.release()} · Python {platform.python_version()}",
            captured_at=time.time(),
        )

    def export_report(self, snapshot: DiagnosticsSnapshot, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(asdict(snapshot), indent=2), encoding="utf-8")
        return output_path

    def _gpu_summary(self) -> str:
        if psutil is None:
            return "Unknown"
        try:
            import torch

            if torch.cuda.is_available():
                return f"CUDA · {torch.cuda.get_device_name(0)}"
        except Exception:
            pass
        return "Not detected"
