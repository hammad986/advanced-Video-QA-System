from __future__ import annotations

from pathlib import Path

import pytest

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.services.task_runner import TaskSignals
from desktop_app.transcripts.transcript_manager import TranscriptManager
from desktop_app.transcripts.transcript_models import (
    Transcript,
    TranscriptStatus,
    TranscriptionResult,
    TranscriptionSegmentResult,
)
from desktop_app.transcripts.transcript_repository import TranscriptRepository
from desktop_app.transcripts.transcript_service import TranscriptService
from desktop_app.transcripts.transcription_worker import (
    CancellationToken,
    TranscriptionError,
    TranscriptionCancelled,
    TranscriptionWorker,
)
from desktop_app.videos.video_metadata import VideoMetadata
from desktop_app.videos.video_model import VideoRecord
from desktop_app.videos.video_repository import VideoRepository


class FakeWorker:
    def __init__(self, *, fail: bool = False, cancel_midway: bool = False) -> None:
        self.fail = fail
        self.cancel_midway = cancel_midway

    def run(self, video_path: Path, token: CancellationToken, progress=None) -> TranscriptionResult:
        _ = video_path
        if progress:
            progress(50, "Halfway")
        if self.cancel_midway:
            token.cancel()
            token.raise_if_cancelled()
        if self.fail:
            raise RuntimeError("corrupted video")
        return TranscriptionResult(
            language="en",
            segments=[
                TranscriptionSegmentResult(0.0, 2.0, "hello world", 0.91),
                TranscriptionSegmentResult(2.0, 4.0, "second segment", 0.88),
            ],
        )


class ImmediateTaskRunner:
    def __init__(self) -> None:
        self.signals = TaskSignals()

    def run(self, callback, task_id=None) -> str:
        resolved = task_id or "task"
        try:
            result = callback()
        except Exception as exc:
            self.signals.failed.emit(resolved, exc)
        else:
            self.signals.finished.emit(resolved, result)
        return resolved


def _video_context(tmp_path, *, count: int = 1, duration: float = 60.0):
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project_service = ProjectService(ProjectRepository(database.connection))
    project = project_service.create_project(name="Project", root_path=str(tmp_path / "project"))
    repository = VideoRepository(database.connection)
    videos: list[VideoRecord] = []
    for index in range(count):
        source = tmp_path / f"video-{index}.mp4"
        source.write_bytes(b"video")
        video = VideoRecord.create(
            project_id=project.id,
            name=source.name,
            file_path=str(source),
            file_size=source.stat().st_size,
            metadata=VideoMetadata(duration=duration, fps=24.0, width=320, height=180),
            thumbnail_path="",
        )
        videos.append(repository.save(video))
    return database, videos


def test_transcript_service_generates_and_persists_segments(tmp_path) -> None:
    database, videos = _video_context(tmp_path)
    repository = TranscriptRepository(database.connection)
    service = TranscriptService(
        repository,
        lambda video_id: videos[0] if video_id == videos[0].id else None,
        worker_factory=lambda _: FakeWorker(),
    )

    transcript = service.generate_transcript(videos[0].id, "base", CancellationToken())
    segments = repository.list_segments(transcript.id)

    assert transcript.status == TranscriptStatus.COMPLETED
    assert transcript.language == "en"
    assert len(segments) == 2
    assert segments[0].text == "hello world"


def test_one_minute_and_thirty_minute_video_paths(tmp_path) -> None:
    one_minute_db, one_minute_videos = _video_context(tmp_path / "one", duration=60.0)
    thirty_minute_db, thirty_minute_videos = _video_context(tmp_path / "thirty", duration=1800.0)

    one_minute_service = TranscriptService(
        TranscriptRepository(one_minute_db.connection),
        lambda video_id: one_minute_videos[0] if video_id == one_minute_videos[0].id else None,
        worker_factory=lambda _: FakeWorker(),
    )
    thirty_minute_service = TranscriptService(
        TranscriptRepository(thirty_minute_db.connection),
        lambda video_id: thirty_minute_videos[0] if video_id == thirty_minute_videos[0].id else None,
        worker_factory=lambda _: FakeWorker(),
    )

    one_minute = one_minute_service.generate_transcript(one_minute_videos[0].id, "tiny", CancellationToken())
    thirty_minute = thirty_minute_service.generate_transcript(thirty_minute_videos[0].id, "medium", CancellationToken())

    assert one_minute.status == TranscriptStatus.COMPLETED
    assert thirty_minute.status == TranscriptStatus.COMPLETED


def test_corrupted_video_marks_transcript_failed(tmp_path) -> None:
    database, videos = _video_context(tmp_path)
    repository = TranscriptRepository(database.connection)
    service = TranscriptService(
        repository,
        lambda video_id: videos[0] if video_id == videos[0].id else None,
        worker_factory=lambda _: FakeWorker(fail=True),
    )

    with pytest.raises(RuntimeError):
        service.generate_transcript(videos[0].id, "base", CancellationToken())

    transcripts = repository.list_by_video(videos[0].id)
    assert transcripts[0].status == TranscriptStatus.FAILED


def test_cancel_midway_marks_transcript_cancelled(tmp_path) -> None:
    database, videos = _video_context(tmp_path)
    repository = TranscriptRepository(database.connection)
    service = TranscriptService(
        repository,
        lambda video_id: videos[0] if video_id == videos[0].id else None,
        worker_factory=lambda _: FakeWorker(cancel_midway=True),
    )

    with pytest.raises(TranscriptionCancelled):
        service.generate_transcript(videos[0].id, "small", CancellationToken())

    transcripts = repository.list_by_video(videos[0].id)
    assert transcripts[0].status == TranscriptStatus.CANCELLED


def test_retry_after_failure_can_complete(tmp_path) -> None:
    database, videos = _video_context(tmp_path)
    repository = TranscriptRepository(database.connection)
    attempts = {"count": 0}

    def worker_factory(_model: str) -> FakeWorker:
        attempts["count"] += 1
        return FakeWorker(fail=attempts["count"] == 1)

    service = TranscriptService(
        repository,
        lambda video_id: videos[0] if video_id == videos[0].id else None,
        worker_factory=worker_factory,
    )

    with pytest.raises(RuntimeError):
        service.generate_transcript(videos[0].id, "base", CancellationToken())
    transcript = service.generate_transcript(videos[0].id, "base", CancellationToken())

    statuses = [item.status for item in repository.list_by_video(videos[0].id)]
    assert transcript.status == TranscriptStatus.COMPLETED
    assert TranscriptStatus.FAILED in statuses
    assert TranscriptStatus.COMPLETED in statuses


def test_multiple_videos_can_be_queued(tmp_path) -> None:
    database, videos = _video_context(tmp_path, count=2)
    repository = TranscriptRepository(database.connection)
    service = TranscriptService(
        repository,
        lambda video_id: next((video for video in videos if video.id == video_id), None),
        worker_factory=lambda _: FakeWorker(),
    )
    manager = TranscriptManager(service, ImmediateTaskRunner())  # type: ignore[arg-type]
    finished = []
    manager.job_finished.connect(finished.append)

    manager.start_transcription(videos[0].id, model_name="tiny")
    manager.start_transcription(videos[1].id, model_name="tiny")

    assert len(finished) == 2
    assert all(state.status == TranscriptStatus.COMPLETED for state in finished)


def test_transcription_worker_rejects_corrupted_video_file(tmp_path) -> None:
    corrupted = tmp_path / "corrupted.mp4"
    corrupted.write_bytes(b"not a valid video")
    worker = TranscriptionWorker(model_name="tiny", engine_factory=lambda _: FakeWorker())

    with pytest.raises(TranscriptionError):
        worker.extract_audio(corrupted, tmp_path / "audio.wav", CancellationToken())
