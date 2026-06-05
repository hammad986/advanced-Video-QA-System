from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, replace
from enum import StrEnum


class HighlightColor(StrEnum):
    YELLOW = "yellow"
    GREEN = "green"
    BLUE = "blue"
    PURPLE = "purple"
    RED = "red"


@dataclass(frozen=True)
class Highlight:
    id: str
    project_id: str
    video_id: str
    transcript_id: str
    segment_id: str
    chunk_id: str
    highlighted_text: str
    color: HighlightColor
    note: str
    timestamp: float
    created_at: float
    updated_at: float

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        highlighted_text: str,
        color: HighlightColor,
        note: str = "",
        video_id: str = "",
        transcript_id: str = "",
        segment_id: str = "",
        chunk_id: str = "",
        timestamp: float = 0.0,
    ) -> "Highlight":
        now = time.time()
        return cls(
            id=str(uuid.uuid4()),
            project_id=project_id,
            video_id=video_id,
            transcript_id=transcript_id,
            segment_id=segment_id,
            chunk_id=chunk_id,
            highlighted_text=highlighted_text.strip(),
            color=color,
            note=note.strip(),
            timestamp=max(0.0, timestamp),
            created_at=now,
            updated_at=now,
        )

    def with_updates(self, *, note: str | None = None, color: HighlightColor | None = None) -> "Highlight":
        return replace(
            self,
            note=self.note if note is None else note.strip(),
            color=self.color if color is None else color,
            updated_at=time.time(),
        )
