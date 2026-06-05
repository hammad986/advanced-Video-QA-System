from __future__ import annotations

import time
import uuid
from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeChunk:
    chunk_id: str
    transcript_id: str
    start_time: float
    end_time: float
    chunk_text: str
    topic_title: str
    confidence: float
    word_count: int
    created_at: float

    @classmethod
    def create(
        cls,
        *,
        transcript_id: str,
        start_time: float,
        end_time: float,
        chunk_text: str,
        topic_title: str,
        confidence: float,
    ) -> "KnowledgeChunk":
        return cls(
            chunk_id=str(uuid.uuid4()),
            transcript_id=transcript_id,
            start_time=start_time,
            end_time=end_time,
            chunk_text=chunk_text,
            topic_title=topic_title,
            confidence=max(0.0, min(confidence, 1.0)),
            word_count=len(chunk_text.split()),
            created_at=time.time(),
        )


@dataclass(frozen=True)
class ChunkTopic:
    id: str
    chunk_id: str
    topic_title: str
    confidence: float

    @classmethod
    def create(cls, *, chunk_id: str, topic_title: str, confidence: float) -> "ChunkTopic":
        return cls(
            id=str(uuid.uuid4()),
            chunk_id=chunk_id,
            topic_title=topic_title,
            confidence=max(0.0, min(confidence, 1.0)),
        )


@dataclass(frozen=True)
class ChunkDraft:
    start_time: float
    end_time: float
    chunk_text: str
    confidence: float

