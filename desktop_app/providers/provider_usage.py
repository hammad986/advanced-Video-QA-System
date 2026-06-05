from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection


@dataclass(frozen=True)
class ProviderUsageRecord:
    id: str
    project_id: str
    provider: str
    model: str
    task_type: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost_usd: float
    response_time_ms: float
    created_at: float

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        provider: str,
        model: str,
        task_type: str,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        estimated_cost_usd: float = 0.0,
        response_time_ms: float = 0.0,
    ) -> "ProviderUsageRecord":
        return cls(
            id=str(uuid.uuid4()),
            project_id=project_id,
            provider=provider,
            model=model,
            task_type=task_type,
            prompt_tokens=max(0, prompt_tokens),
            completion_tokens=max(0, completion_tokens),
            total_tokens=max(0, total_tokens),
            estimated_cost_usd=max(0.0, estimated_cost_usd),
            response_time_ms=max(0.0, response_time_ms),
            created_at=time.time(),
        )


@dataclass(frozen=True)
class ProviderUsageSummary:
    project_id: str
    total_requests: int
    total_tokens: int
    estimated_cost_usd: float
    average_response_time_ms: float
    by_provider: dict[str, dict[str, float]]


class ProviderCostEstimator:
    DEFAULT_RATES_PER_1K: dict[str, float] = {
        "gemini": 0.00025,
        "openai": 0.00060,
        "huggingface": 0.00010,
        "groq": 0.00020,
        "openrouter": 0.00050,
        "local": 0.0,
        "local_validation_fake": 0.0,
    }

    def estimate(self, *, provider: str, total_tokens: int) -> float:
        rate = self.DEFAULT_RATES_PER_1K.get(provider.lower(), 0.00050)
        return (max(0, total_tokens) / 1000.0) * rate


class ProviderUsageRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save(self, record: ProviderUsageRecord) -> ProviderUsageRecord:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO provider_usage (
                    id, project_id, provider, model, task_type,
                    prompt_tokens, completion_tokens, total_tokens,
                    estimated_cost_usd, response_time_ms, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.project_id,
                    record.provider,
                    record.model,
                    record.task_type,
                    record.prompt_tokens,
                    record.completion_tokens,
                    record.total_tokens,
                    record.estimated_cost_usd,
                    record.response_time_ms,
                    record.created_at,
                ),
            )
        return record

    def list_by_project(self, project_id: str, *, limit: int = 1000) -> list[ProviderUsageRecord]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM provider_usage
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def summarize(self, project_id: str) -> ProviderUsageSummary:
        records = self.list_by_project(project_id)
        by_provider: dict[str, dict[str, float]] = {}
        for record in records:
            bucket = by_provider.setdefault(
                record.provider,
                {"requests": 0, "tokens": 0, "cost_usd": 0.0, "response_time_ms": 0.0},
            )
            bucket["requests"] += 1
            bucket["tokens"] += record.total_tokens
            bucket["cost_usd"] += record.estimated_cost_usd
            bucket["response_time_ms"] += record.response_time_ms
        total_requests = len(records)
        total_tokens = sum(record.total_tokens for record in records)
        total_cost = sum(record.estimated_cost_usd for record in records)
        total_response = sum(record.response_time_ms for record in records)
        for bucket in by_provider.values():
            requests = max(1.0, bucket["requests"])
            bucket["average_response_time_ms"] = bucket["response_time_ms"] / requests
        return ProviderUsageSummary(
            project_id=project_id,
            total_requests=total_requests,
            total_tokens=total_tokens,
            estimated_cost_usd=total_cost,
            average_response_time_ms=total_response / max(1, total_requests),
            by_provider=by_provider,
        )

    def _row_to_record(self, row: Row) -> ProviderUsageRecord:
        return ProviderUsageRecord(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            provider=str(row["provider"]),
            model=str(row["model"]),
            task_type=str(row["task_type"]),
            prompt_tokens=int(row["prompt_tokens"]),
            completion_tokens=int(row["completion_tokens"]),
            total_tokens=int(row["total_tokens"]),
            estimated_cost_usd=float(row["estimated_cost_usd"]),
            response_time_ms=float(row["response_time_ms"]),
            created_at=float(row["created_at"]),
        )


class ProviderUsageService:
    def __init__(
        self,
        repository: ProviderUsageRepository,
        estimator: ProviderCostEstimator | None = None,
    ) -> None:
        self.repository = repository
        self.estimator = estimator or ProviderCostEstimator()

    def record(
        self,
        *,
        project_id: str,
        provider: str,
        model: str,
        task_type: str,
        token_usage: dict[str, int] | None,
        response_time_ms: float,
    ) -> ProviderUsageRecord:
        usage = token_usage or {}
        prompt_tokens = int(usage.get("prompt_tokens", 0) or 0)
        completion_tokens = int(usage.get("completion_tokens", 0) or 0)
        total_tokens = int(usage.get("total_tokens", prompt_tokens + completion_tokens) or 0)
        estimated_cost = self.estimator.estimate(provider=provider, total_tokens=total_tokens)
        return self.repository.save(
            ProviderUsageRecord.create(
                project_id=project_id,
                provider=provider,
                model=model,
                task_type=task_type,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=estimated_cost,
                response_time_ms=response_time_ms,
            )
        )
