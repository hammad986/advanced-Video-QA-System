from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, replace

from desktop_app.videos.video_metadata import VideoMetadata


@dataclass(frozen=True)
class VideoRecord:
    id: str
    project_id: str
    name: str
    file_path: str
    file_size: int
    duration: float
    fps: float
    width: int
    height: int
    thumbnail_path: str
    created_at: float
    updated_at: float

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        name: str,
        file_path: str,
        file_size: int,
        metadata: VideoMetadata,
        thumbnail_path: str,
    ) -> "VideoRecord":
        now = time.time()
        return cls(
            id=str(uuid.uuid4()),
            project_id=project_id,
            name=name,
            file_path=file_path,
            file_size=file_size,
            duration=metadata.duration,
            fps=metadata.fps,
            width=metadata.width,
            height=metadata.height,
            thumbnail_path=thumbnail_path,
            created_at=now,
            updated_at=now,
        )

    def with_updates(self, **changes: object) -> "VideoRecord":
        return replace(self, updated_at=time.time(), **changes)

