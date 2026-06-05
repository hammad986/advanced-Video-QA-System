from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from desktop_app.answering.answer_models import Citation
from desktop_app.evidence.evidence_models import EvidenceItem


class ChatSessionStatus(StrEnum):
    ACTIVE = "active"
    DELETED = "deleted"


class ChatJobStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class ChatSession:
    id: str
    project_id: str
    title: str
    status: ChatSessionStatus
    created_at: float
    updated_at: float
    last_message_at: float | None = None
    deleted_at: float | None = None

    @classmethod
    def create(cls, *, project_id: str, title: str = "New Chat") -> "ChatSession":
        now = time.time()
        return cls(
            id=str(uuid.uuid4()),
            project_id=project_id,
            title=title,
            status=ChatSessionStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )


@dataclass(frozen=True)
class ChatMessage:
    id: str
    session_id: str
    project_id: str
    question: str
    answer: str
    citations_json: str
    provider: str
    provider_model: str
    duration_ms: float
    token_usage_json: str
    created_at: float
    citations: list[Citation] = field(default_factory=list)
    evidence_items: list[EvidenceItem] = field(default_factory=list)

    @classmethod
    def create(
        cls,
        *,
        session_id: str,
        project_id: str,
        question: str,
        answer: str,
        citations_json: str,
        provider: str,
        provider_model: str = "",
        duration_ms: float = 0.0,
        token_usage_json: str = "{}",
        citations: list[Citation] | None = None,
        evidence_items: list[EvidenceItem] | None = None,
    ) -> "ChatMessage":
        return cls(
            id=str(uuid.uuid4()),
            session_id=session_id,
            project_id=project_id,
            question=question,
            answer=answer,
            citations_json=citations_json,
            provider=provider,
            provider_model=provider_model,
            duration_ms=duration_ms,
            token_usage_json=token_usage_json,
            created_at=time.time(),
            citations=citations or [],
            evidence_items=evidence_items or [],
        )


@dataclass(frozen=True)
class ChatSearchResult:
    session: ChatSession
    message: ChatMessage


@dataclass(frozen=True)
class ChatJobState:
    job_id: str
    session_id: str
    project_id: str
    question: str
    status: ChatJobStatus
    progress_percent: int = 0
    provider: str = ""
    duration_ms: float = 0.0
    error_message: str = ""
