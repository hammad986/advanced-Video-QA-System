from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from enum import StrEnum


class TranscriptStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TranscriptModelName(StrEnum):
    TINY = "tiny"
    BASE = "base"
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


@dataclass(frozen=True)
class Transcript:
    id: str
    video_id: str
    language: str
    model_name: str
    status: TranscriptStatus
    created_at: float

    @classmethod
    def create(
        cls,
        *,
        video_id: str,
        model_name: str,
        language: str = "",
        status: TranscriptStatus = TranscriptStatus.QUEUED,
    ) -> "Transcript":
        return cls(
            id=str(uuid.uuid4()),
            video_id=video_id,
            language=language,
            model_name=model_name,
            status=status,
            created_at=time.time(),
        )


@dataclass(frozen=True)
class TranscriptSegment:
    id: str
    transcript_id: str
    start_time: float
    end_time: float
    text: str
    confidence: float

    @classmethod
    def create(
        cls,
        *,
        transcript_id: str,
        start_time: float,
        end_time: float,
        text: str,
        confidence: float = 0.0,
    ) -> "TranscriptSegment":
        return cls(
            id=str(uuid.uuid4()),
            transcript_id=transcript_id,
            start_time=start_time,
            end_time=end_time,
            text=text,
            confidence=confidence,
        )


@dataclass(frozen=True)
class TranscriptionSegmentResult:
    start_time: float
    end_time: float
    text: str
    confidence: float = 0.0


@dataclass(frozen=True)
class TranscriptionResult:
    language: str
    segments: list[TranscriptionSegmentResult]


@dataclass(frozen=True)
class TranscriptJobState:
    job_id: str
    video_id: str
    model_name: str
    status: TranscriptStatus
    progress_percent: int = 0
    transcript_id: str | None = None
    error_message: str = ""

