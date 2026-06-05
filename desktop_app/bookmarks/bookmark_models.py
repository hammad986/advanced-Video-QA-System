from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, replace
from enum import StrEnum


class BookmarkType(StrEnum):
    EVIDENCE = "evidence"
    TRANSCRIPT_SEGMENT = "transcript_segment"
    VIDEO_TIMESTAMP = "video_timestamp"


@dataclass(frozen=True)
class Bookmark:
    id: str
    project_id: str
    video_id: str
    chunk_id: str
    transcript_id: str
    segment_id: str
    bookmark_type: BookmarkType
    title: str
    note: str
    timestamp: float
    source_text: str
    created_at: float
    updated_at: float

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        bookmark_type: BookmarkType,
        title: str,
        note: str = "",
        video_id: str = "",
        chunk_id: str = "",
        transcript_id: str = "",
        segment_id: str = "",
        timestamp: float = 0.0,
        source_text: str = "",
    ) -> "Bookmark":
        now = time.time()
        return cls(
            id=str(uuid.uuid4()),
            project_id=project_id,
            video_id=video_id,
            chunk_id=chunk_id,
            transcript_id=transcript_id,
            segment_id=segment_id,
            bookmark_type=bookmark_type,
            title=title.strip() or "Untitled Bookmark",
            note=note.strip(),
            timestamp=max(0.0, timestamp),
            source_text=source_text.strip(),
            created_at=now,
            updated_at=now,
        )

    def with_updates(self, *, title: str | None = None, note: str | None = None) -> "Bookmark":
        return replace(
            self,
            title=self.title if title is None else title.strip() or "Untitled Bookmark",
            note=self.note if note is None else note.strip(),
            updated_at=time.time(),
        )
