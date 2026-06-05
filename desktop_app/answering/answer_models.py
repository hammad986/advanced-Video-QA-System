from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import StrEnum

from desktop_app.evidence.evidence_models import EvidenceItem


INSUFFICIENT_EVIDENCE_RESPONSE = "I could not find enough evidence in the loaded videos."


class AnswerStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class Citation:
    citation_id: int
    source_video: str
    chunk_id: str
    timestamp_start: float
    timestamp_end: float
    confidence: float
    source_video_id: str = ""
    source_file_path: str = ""

    def label(self) -> str:
        return f"[{self.citation_id}] {self.source_video} @ {self.timestamp_start:.1f}s-{self.timestamp_end:.1f}s"


@dataclass(frozen=True)
class AnswerResult:
    project_id: str
    question: str
    answer: str
    provider: str
    citations: list[Citation]
    evidence_items: list[EvidenceItem]
    duration_ms: float
    created_at: float
    provider_model: str = ""
    token_usage: dict[str, int] | None = None


@dataclass(frozen=True)
class ChatHistoryRecord:
    id: str
    project_id: str
    question: str
    answer: str
    citations_json: str
    provider: str
    duration_ms: float
    created_at: float
    updated_at: float

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        question: str,
        answer: str,
        citations_json: str,
        provider: str,
        duration_ms: float,
    ) -> "ChatHistoryRecord":
        now = time.time()
        return cls(
            id=str(uuid.uuid4()),
            project_id=project_id,
            question=question,
            answer=answer,
            citations_json=citations_json,
            provider=provider,
            duration_ms=duration_ms,
            created_at=now,
            updated_at=now,
        )


@dataclass(frozen=True)
class AnswerJobState:
    job_id: str
    project_id: str
    question: str
    status: AnswerStatus
    progress_percent: int = 0
    provider: str = ""
    duration_ms: float = 0.0
    error_message: str = ""
