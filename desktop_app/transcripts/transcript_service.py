from __future__ import annotations

from pathlib import Path
from typing import Callable

from desktop_app.transcripts.transcript_models import (
    Transcript,
    TranscriptSegment,
    TranscriptStatus,
)
from desktop_app.transcripts.transcript_repository import TranscriptRepository
from desktop_app.transcripts.transcription_worker import (
    CancellationToken,
    ProgressCallback,
    TranscriptionCancelled,
    TranscriptionWorker,
)
from desktop_app.videos.video_model import VideoRecord


class TranscriptService:
    def __init__(
        self,
        repository: TranscriptRepository,
        get_video: Callable[[str], VideoRecord | None],
        *,
        worker_factory: Callable[[str], TranscriptionWorker] | None = None,
    ) -> None:
        self.repository = repository
        self.get_video = get_video
        self.worker_factory = worker_factory or (lambda model: TranscriptionWorker(model_name=model))

    def generate_transcript(
        self,
        video_id: str,
        model_name: str,
        token: CancellationToken,
        progress: ProgressCallback | None = None,
    ) -> Transcript:
        video = self.get_video(video_id)
        if video is None:
            raise ValueError("Video was not found.")
        transcript = Transcript.create(
            video_id=video_id,
            model_name=model_name,
            status=TranscriptStatus.RUNNING,
        )
        self.repository.save_transcript(transcript)
        try:
            worker = self.worker_factory(model_name)
            result = worker.run(Path(video.file_path), token, progress)
        except TranscriptionCancelled:
            self.repository.update_status(transcript.id, TranscriptStatus.CANCELLED)
            raise
        except Exception:
            self.repository.update_status(transcript.id, TranscriptStatus.FAILED)
            raise

        segments = [
            TranscriptSegment.create(
                transcript_id=transcript.id,
                start_time=segment.start_time,
                end_time=segment.end_time,
                text=segment.text,
                confidence=segment.confidence,
            )
            for segment in result.segments
        ]
        self.repository.replace_segments(transcript.id, segments)
        self.repository.update_status(
            transcript.id,
            TranscriptStatus.COMPLETED,
            language=result.language,
        )
        completed = self.repository.get_transcript(transcript.id)
        if completed is None:
            raise RuntimeError("Transcript was not persisted.")
        if progress:
            progress(100, "Transcript complete")
        return completed

    def list_video_transcripts(self, video_id: str) -> list[Transcript]:
        return self.repository.list_by_video(video_id)

