from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import StrEnum


class EvidenceStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class EvidenceSource:
    video_id: str
    video_name: str
    file_path: str
    transcript_id: str


@dataclass(frozen=True)
class EvidenceItem:
    id: str
    project_id: str
    query: str
    chunk_id: str
    retrieval_rank: int
    source: EvidenceSource
    topic_title: str
    start_time: float
    end_time: float
    similarity_score: float
    confidence_score: float
    chunk_text: str

    @property
    def start_ms(self) -> int:
        return int(self.start_time * 1000)

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        query: str,
        chunk_id: str,
        retrieval_rank: int,
        source: EvidenceSource,
        topic_title: str,
        start_time: float,
        end_time: float,
        similarity_score: float,
        confidence_score: float,
        chunk_text: str,
    ) -> "EvidenceItem":
        return cls(
            id=str(uuid.uuid4()),
            project_id=project_id,
            query=query,
            chunk_id=chunk_id,
            retrieval_rank=retrieval_rank,
            source=source,
            topic_title=topic_title,
            start_time=start_time,
            end_time=end_time,
            similarity_score=similarity_score,
            confidence_score=confidence_score,
            chunk_text=chunk_text,
        )


@dataclass(frozen=True)
class EvidenceHistoryRecord:
    id: str
    project_id: str
    query: str
    chunk_id: str
    rank: int
    similarity_score: float
    confidence_score: float
    created_at: float

    @classmethod
    def from_item(cls, item: EvidenceItem) -> "EvidenceHistoryRecord":
        return cls(
            id=str(uuid.uuid4()),
            project_id=item.project_id,
            query=item.query,
            chunk_id=item.chunk_id,
            rank=item.retrieval_rank,
            similarity_score=item.similarity_score,
            confidence_score=item.confidence_score,
            created_at=time.time(),
        )


@dataclass(frozen=True)
class EvidenceResult:
    project_id: str
    query: str
    duration_ms: float
    items: list[EvidenceItem]


@dataclass(frozen=True)
class EvidenceJobState:
    job_id: str
    project_id: str
    query: str
    status: EvidenceStatus
    progress_percent: int = 0
    item_count: int = 0
    duration_ms: float = 0.0
    error_message: str = ""
