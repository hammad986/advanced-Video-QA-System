from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import StrEnum


class RetrievalStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class RetrievalHistoryRecord:
    id: str
    project_id: str
    query: str
    embedding_model: str
    top_k: int
    duration_ms: float
    created_at: float

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        query: str,
        embedding_model: str,
        top_k: int,
        duration_ms: float,
    ) -> "RetrievalHistoryRecord":
        return cls(
            id=str(uuid.uuid4()),
            project_id=project_id,
            query=query,
            embedding_model=embedding_model,
            top_k=top_k,
            duration_ms=duration_ms,
            created_at=time.time(),
        )


@dataclass(frozen=True)
class RetrievalChunk:
    chunk_id: str
    transcript_id: str
    start_time: float
    end_time: float
    chunk_text: str
    topic_title: str
    confidence: float
    word_count: int


@dataclass(frozen=True)
class RetrievalHit:
    chunk: RetrievalChunk
    rank: int
    raw_score: float
    similarity_score: float
    confidence_score: float
    topic_score: float


@dataclass(frozen=True)
class RetrievalResult:
    project_id: str
    query: str
    embedding_model: str
    top_k: int
    duration_ms: float
    hits: list[RetrievalHit]


@dataclass(frozen=True)
class RetrievalJobState:
    job_id: str
    project_id: str
    query: str
    status: RetrievalStatus
    progress_percent: int = 0
    hit_count: int = 0
    duration_ms: float = 0.0
    error_message: str = ""
