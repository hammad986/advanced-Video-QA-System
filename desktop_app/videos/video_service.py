from __future__ import annotations

import shutil
from pathlib import Path

from desktop_app.projects.project_service import ProjectService
from desktop_app.videos.thumbnail_generator import ThumbnailGenerator
from desktop_app.videos.video_metadata import VideoMetadataExtractor
from desktop_app.videos.video_model import VideoRecord
from desktop_app.videos.video_repository import VideoRepository


class VideoImportError(RuntimeError):
    pass


class UnsupportedVideoError(VideoImportError):
    pass


class MissingVideoError(VideoImportError):
    pass


class DuplicateVideoError(VideoImportError):
    pass


class VideoService:
    SUPPORTED_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".webm"}

    def __init__(
        self,
        video_repository: VideoRepository,
        project_service: ProjectService,
        *,
        metadata_extractor: VideoMetadataExtractor | None = None,
        thumbnail_generator: ThumbnailGenerator | None = None,
    ) -> None:
        self.video_repository = video_repository
        self.project_service = project_service
        self.metadata_extractor = metadata_extractor or VideoMetadataExtractor()
        self.thumbnail_generator = thumbnail_generator or ThumbnailGenerator()

    def import_video(self, project_id: str, source_path: str | Path) -> VideoRecord:
        project = self.project_service.get_project(project_id)
        if project is None:
            raise VideoImportError("Project does not exist.")

        source = Path(source_path).expanduser().resolve()
        if not source.exists() or not source.is_file():
            raise MissingVideoError(f"Video file not found: {source}")
        if source.suffix.lower() not in self.SUPPORTED_EXTENSIONS:
            raise UnsupportedVideoError(f"Unsupported video format: {source.suffix}")

        project_root = Path(project.root_path)
        videos_dir = project_root / "Videos"
        thumbnails_dir = project_root / "Thumbnails"
        videos_dir.mkdir(parents=True, exist_ok=True)
        thumbnails_dir.mkdir(parents=True, exist_ok=True)

        target = videos_dir / source.name
        existing = self.video_repository.find_by_project_path(project_id, str(target))
        if existing is not None:
            raise DuplicateVideoError(f"Video already exists in this project: {source.name}")
        if target.exists():
            raise DuplicateVideoError(f"Video file already exists in the project workspace: {source.name}")

        metadata = self.metadata_extractor.extract(source)
        shutil.copy2(source, target)

        video = VideoRecord.create(
            project_id=project_id,
            name=target.name,
            file_path=str(target),
            file_size=target.stat().st_size,
            metadata=metadata,
            thumbnail_path="",
        )
        thumbnail_path = thumbnails_dir / f"{video.id}.jpg"
        thumbnail = self.thumbnail_generator.generate(target, thumbnail_path, duration=metadata.duration)
        return self.video_repository.save(video.with_updates(thumbnail_path=str(thumbnail)))

    def import_videos(self, project_id: str, source_paths: list[str | Path]) -> list[VideoRecord]:
        imported: list[VideoRecord] = []
        for source_path in source_paths:
            imported.append(self.import_video(project_id, source_path))
        return imported

    def list_project_videos(self, project_id: str, *, search: str = "") -> list[VideoRecord]:
        return self.video_repository.list_by_project(project_id, search=search)

    def get_video(self, video_id: str) -> VideoRecord | None:
        return self.video_repository.get(video_id)

    def remove_video(self, video_id: str) -> bool:
        return self.video_repository.delete(video_id)
