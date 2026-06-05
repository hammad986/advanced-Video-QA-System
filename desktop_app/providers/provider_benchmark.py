from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection


@dataclass(frozen=True)
class ProviderBenchmarkRecord:
    id: str
    provider: str
    model: str
    task_type: str
    success: bool
    latency_ms: float
    error_message: str
    created_at: float

    @classmethod
    def create(
        cls,
        *,
        provider: str,
        model: str,
        task_type: str,
        success: bool,
        latency_ms: float,
        error_message: str = "",
    ) -> "ProviderBenchmarkRecord":
        return cls(
            id=str(uuid.uuid4()),
            provider=provider,
            model=model,
            task_type=task_type,
            success=success,
            latency_ms=max(0.0, latency_ms),
            error_message=error_message[:500],
            created_at=time.time(),
        )


@dataclass(frozen=True)
class ProviderBenchmarkSummary:
    provider: str
    task_type: str
    samples: int
    success_rate: float
    failure_rate: float
    average_latency_ms: float


class ProviderBenchmarkRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save(self, record: ProviderBenchmarkRecord) -> ProviderBenchmarkRecord:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO provider_benchmarks (
                    id, provider, model, task_type, success,
                    latency_ms, error_message, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.provider,
                    record.model,
                    record.task_type,
                    int(record.success),
                    record.latency_ms,
                    record.error_message,
                    record.created_at,
                ),
            )
        return record

    def list_recent(self, *, provider: str = "", task_type: str = "", limit: int = 100) -> list[ProviderBenchmarkRecord]:
        clauses: list[str] = []
        params: list[object] = []
        if provider:
            clauses.append("provider = ?")
            params.append(provider)
        if task_type:
            clauses.append("task_type = ?")
            params.append(task_type)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        params.append(limit)
        with self.connection.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM provider_benchmarks
                {where}
                ORDER BY created_at DESC
                LIMIT ?
                """,
                tuple(params),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def summarize(self, *, provider: str, task_type: str = "", limit: int = 100) -> ProviderBenchmarkSummary:
        records = self.list_recent(provider=provider, task_type=task_type, limit=limit)
        if not records:
            return ProviderBenchmarkSummary(provider, task_type, 0, 0.0, 0.0, 0.0)
        success_count = sum(1 for record in records if record.success)
        return ProviderBenchmarkSummary(
            provider=provider,
            task_type=task_type,
            samples=len(records),
            success_rate=success_count / len(records),
            failure_rate=(len(records) - success_count) / len(records),
            average_latency_ms=sum(record.latency_ms for record in records) / len(records),
        )

    def _row_to_record(self, row: Row) -> ProviderBenchmarkRecord:
        return ProviderBenchmarkRecord(
            id=str(row["id"]),
            provider=str(row["provider"]),
            model=str(row["model"]),
            task_type=str(row["task_type"]),
            success=bool(row["success"]),
            latency_ms=float(row["latency_ms"]),
            error_message=str(row["error_message"]),
            created_at=float(row["created_at"]),
        )


class ProviderBenchmarkService:
    def __init__(self, repository: ProviderBenchmarkRepository) -> None:
        self.repository = repository

    def record_success(self, *, provider: str, model: str, task_type: str, latency_ms: float) -> ProviderBenchmarkRecord:
        return self.repository.save(
            ProviderBenchmarkRecord.create(
                provider=provider,
                model=model,
                task_type=task_type,
                success=True,
                latency_ms=latency_ms,
            )
        )

    def record_failure(
        self,
        *,
        provider: str,
        model: str,
        task_type: str,
        latency_ms: float,
        error_message: str,
    ) -> ProviderBenchmarkRecord:
        return self.repository.save(
            ProviderBenchmarkRecord.create(
                provider=provider,
                model=model,
                task_type=task_type,
                success=False,
                latency_ms=latency_ms,
                error_message=error_message,
            )
        )
