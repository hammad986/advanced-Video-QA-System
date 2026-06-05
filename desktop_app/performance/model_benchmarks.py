from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModelBenchmarkRecord:
    worker_name: str
    model_name: str
    operation: str
    cold_start: bool
    duration_seconds: float
    created_at: float


class ModelBenchmarkHistory:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(
        self,
        *,
        worker_name: str,
        model_name: str,
        operation: str,
        cold_start: bool,
        duration_seconds: float,
    ) -> ModelBenchmarkRecord:
        record = ModelBenchmarkRecord(
            worker_name=worker_name,
            model_name=model_name,
            operation=operation,
            cold_start=cold_start,
            duration_seconds=duration_seconds,
            created_at=time.time(),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        records = self.list_records()
        records.append(record)
        self.path.write_text(
            json.dumps([asdict(item) for item in records[-250:]], indent=2),
            encoding="utf-8",
        )
        return record

    def list_records(self) -> list[ModelBenchmarkRecord]:
        if not self.path.exists():
            return []
        try:
            payload = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return []
        return [ModelBenchmarkRecord(**item) for item in payload if isinstance(item, dict)]

