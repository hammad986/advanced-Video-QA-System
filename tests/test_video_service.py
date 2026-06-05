from __future__ import annotations

from pathlib import Path

import pytest

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.videos.thumbnail_generator import ThumbnailGenerator
from desktop_app.videos.video_metadata import VideoMetadata, VideoMetadataError, VideoMetadataExtractor
from desktop_app.videos.video_repository import VideoRepository
from desktop_app.videos.video_service import (
    DuplicateVideoError,
    MissingVideoError,
    VideoService,
)


class FakeMetadataExtractor(VideoMetadataExtractor):
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail

    def extract(self, video_path: Path) -> VideoMetadata:
        _ = video_path
        if self.fail:
            raise VideoMetadataError("corrupted video")
        return VideoMetadata(duration=123.4, fps=29.97, width=1920, height=1080)


class FakeThumbnailGenerator(ThumbnailGenerator):
    def generate(self, video_path: Path, thumbnail_path: Path, *, duration: float) -> Path:
        _ = video_path
        _ = duration
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        thumbnail_path.write_bytes(b"fake-thumbnail")
        return thumbnail_path


@pytest.fixture()
def video_context(tmp_path):
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project_service = ProjectService(ProjectRepository(database.connection))
    project = project_service.create_project(
        name="Video Project",
        root_path=str(tmp_path / "project"),
    )
    service = VideoService(
        VideoRepository(database.connection),
        project_service,
        metadata_extractor=FakeMetadataExtractor(),
        thumbnail_generator=FakeThumbnailGenerator(),
    )
    return service, project


def _write_video(path: Path, size: int = 128) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"0" * size)
    return path


def test_single_video_import(video_context, tmp_path) -> None:
    service, project = video_context
    source = _write_video(tmp_path / "source" / "lesson.mp4", 2048)

    video = service.import_video(project.id, source)

    assert video.project_id == project.id
    assert video.name == "lesson.mp4"
    assert video.file_size == 2048
    assert video.duration == 123.4
    assert video.fps == 29.97
    assert video.width == 1920
    assert video.height == 1080
    assert Path(video.file_path).exists()
    assert Path(video.thumbnail_path).exists()


def test_100_video_import(video_context, tmp_path) -> None:
    service, project = video_context
    sources = [_write_video(tmp_path / "bulk" / f"video-{index:03d}.mp4") for index in range(100)]

    videos = service.import_videos(project.id, sources)

    assert len(videos) == 100
    assert len(service.list_project_videos(project.id)) == 100


def test_corrupted_video_import_fails(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project_service = ProjectService(ProjectRepository(database.connection))
    project = project_service.create_project(name="Project", root_path=str(tmp_path / "project"))
    service = VideoService(
        VideoRepository(database.connection),
        project_service,
        metadata_extractor=FakeMetadataExtractor(fail=True),
        thumbnail_generator=FakeThumbnailGenerator(),
    )
    source = _write_video(tmp_path / "broken.mp4")

    with pytest.raises(VideoMetadataError):
        service.import_video(project.id, source)


def test_missing_video_import_fails(video_context, tmp_path) -> None:
    service, project = video_context

    with pytest.raises(MissingVideoError):
        service.import_video(project.id, tmp_path / "missing.mp4")


def test_duplicate_video_import_fails(video_context, tmp_path) -> None:
    service, project = video_context
    source = _write_video(tmp_path / "source" / "duplicate.mp4")

    service.import_video(project.id, source)

    with pytest.raises(DuplicateVideoError):
        service.import_video(project.id, source)


def test_large_video_import_records_file_size(video_context, tmp_path) -> None:
    service, project = video_context
    source = tmp_path / "source" / "large.webm"
    source.parent.mkdir(parents=True, exist_ok=True)
    with source.open("wb") as handle:
        handle.seek((10 * 1024 * 1024) - 1)
        handle.write(b"0")

    video = service.import_video(project.id, source)

    assert video.file_size == 10 * 1024 * 1024
