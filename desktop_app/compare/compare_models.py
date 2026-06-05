from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from enum import StrEnum

from desktop_app.evidence.evidence_models import EvidenceItem
from desktop_app.videos.video_model import VideoRecord


class CompareStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CompareFindingType(StrEnum):
    AGREEMENT = "agreement"
    DIFFERENCE = "difference"
    UNIQUE_CONCEPT = "unique_concept"
    MISSING_TOPIC = "missing_topic"
    CONTRADICTION = "contradiction"
    TIMELINE_DIFFERENCE = "timeline_difference"


@dataclass(frozen=True)
class CompareTopic:
    video_id: str
    video_name: str
    topic_title: str
    chunk_id: str
    chunk_text: str
    start_time: float
    end_time: float
    confidence: float


@dataclass(frozen=True)
class CompareFinding:
    finding_type: CompareFindingType
    title: str
    summary: str
    video_ids: list[str]
    evidence_items: list[EvidenceItem] = field(default_factory=list)
    confidence: float = 0.0


@dataclass(frozen=True)
class CompareResult:
    project_id: str
    session_name: str
    video_ids: list[str]
    query: str
    video_sources: list[VideoRecord]
    agreements: list[CompareFinding]
    differences: list[CompareFinding]
    unique_concepts: list[CompareFinding]
    missing_topics: list[CompareFinding]
    contradictions: list[CompareFinding]
    timeline_differences: list[CompareFinding]
    evidence_items: list[EvidenceItem]
    duration_ms: float
    created_at: float

    def to_json(self) -> str:
        return json.dumps(
            {
                "project_id": self.project_id,
                "session_name": self.session_name,
                "video_ids": self.video_ids,
                "query": self.query,
                "video_sources": [
                    {
                        "id": video.id,
                        "name": video.name,
                        "file_path": video.file_path,
                        "duration": video.duration,
                    }
                    for video in self.video_sources
                ],
                "agreements": [_finding_to_dict(finding) for finding in self.agreements],
                "differences": [_finding_to_dict(finding) for finding in self.differences],
                "unique_concepts": [_finding_to_dict(finding) for finding in self.unique_concepts],
                "missing_topics": [_finding_to_dict(finding) for finding in self.missing_topics],
                "contradictions": [_finding_to_dict(finding) for finding in self.contradictions],
                "timeline_differences": [_finding_to_dict(finding) for finding in self.timeline_differences],
                "evidence_items": [_evidence_to_dict(item) for item in self.evidence_items],
                "duration_ms": self.duration_ms,
                "created_at": self.created_at,
            },
            indent=2,
        )


@dataclass(frozen=True)
class CompareSessionRecord:
    id: str
    project_id: str
    session_name: str
    videos_json: str
    query: str
    result_json: str
    created_at: float

    @classmethod
    def create(cls, *, result: CompareResult) -> "CompareSessionRecord":
        return cls(
            id=str(uuid.uuid4()),
            project_id=result.project_id,
            session_name=result.session_name,
            videos_json=json.dumps(result.video_ids, indent=2),
            query=result.query,
            result_json=result.to_json(),
            created_at=time.time(),
        )


@dataclass(frozen=True)
class CompareJobState:
    job_id: str
    project_id: str
    query: str
    status: CompareStatus
    progress_percent: int = 0
    finding_count: int = 0
    duration_ms: float = 0.0
    error_message: str = ""


def _finding_to_dict(finding: CompareFinding) -> dict[str, object]:
    return {
        "finding_type": finding.finding_type.value,
        "title": finding.title,
        "summary": finding.summary,
        "video_ids": finding.video_ids,
        "confidence": finding.confidence,
        "evidence_items": [_evidence_to_dict(item) for item in finding.evidence_items],
    }


def _evidence_to_dict(item: EvidenceItem) -> dict[str, object]:
    return {
        "id": item.id,
        "project_id": item.project_id,
        "query": item.query,
        "chunk_id": item.chunk_id,
        "retrieval_rank": item.retrieval_rank,
        "source": {
            "video_id": item.source.video_id,
            "video_name": item.source.video_name,
            "file_path": item.source.file_path,
            "transcript_id": item.source.transcript_id,
        },
        "topic_title": item.topic_title,
        "start_time": item.start_time,
        "end_time": item.end_time,
        "similarity_score": item.similarity_score,
        "confidence_score": item.confidence_score,
        "chunk_text": item.chunk_text,
    }
