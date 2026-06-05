from __future__ import annotations

import uuid

from PySide6.QtCore import QObject, Signal

from desktop_app.services.task_runner import TaskRunner
from desktop_app.transcripts.transcript_models import TranscriptJobState, TranscriptStatus
from desktop_app.transcripts.transcript_service import TranscriptService
from desktop_app.transcripts.transcription_worker import CancellationToken, TranscriptionCancelled


class TranscriptManager(QObject):
    job_queued = Signal(object)
    progress_changed = Signal(object)
    job_finished = Signal(object)
    job_failed = Signal(object)

    def __init__(self, transcript_service: TranscriptService, task_runner: TaskRunner) -> None:
        super().__init__()
        self.transcript_service = transcript_service
        self.task_runner = task_runner
        self._tokens: dict[str, CancellationToken] = {}
        self._states: dict[str, TranscriptJobState] = {}
        self.task_runner.signals.finished.connect(self._handle_task_finished)
        self.task_runner.signals.failed.connect(self._handle_task_failed)

    def start_transcription(self, video_id: str, *, model_name: str = "base") -> str:
        job_id = f"transcript-{uuid.uuid4().hex}"
        token = CancellationToken()
        state = TranscriptJobState(
            job_id=job_id,
            video_id=video_id,
            model_name=model_name,
            status=TranscriptStatus.QUEUED,
        )
        self._tokens[job_id] = token
        self._states[job_id] = state
        self.job_queued.emit(state)

        def run_job() -> object:
            self._set_progress(job_id, 1, "Queued", TranscriptStatus.RUNNING)
            transcript = self.transcript_service.generate_transcript(
                video_id,
                model_name,
                token,
                progress=lambda percent, message: self._set_progress(
                    job_id,
                    percent,
                    message,
                    TranscriptStatus.RUNNING,
                ),
            )
            return transcript

        self.task_runner.run(run_job, task_id=job_id)
        return job_id

    def cancel(self, job_id: str) -> None:
        token = self._tokens.get(job_id)
        if token is None:
            return
        token.cancel()
        self._set_progress(job_id, 0, "Cancelling", TranscriptStatus.CANCELLED)

    def retry(self, video_id: str, *, model_name: str = "base") -> str:
        return self.start_transcription(video_id, model_name=model_name)

    def _set_progress(
        self,
        job_id: str,
        percent: int,
        message: str,
        status: TranscriptStatus,
    ) -> None:
        state = self._states.get(job_id)
        if state is None:
            return
        updated = TranscriptJobState(
            job_id=state.job_id,
            video_id=state.video_id,
            model_name=state.model_name,
            status=status,
            progress_percent=max(0, min(percent, 100)),
            transcript_id=state.transcript_id,
            error_message=message,
        )
        self._states[job_id] = updated
        self.progress_changed.emit(updated)

    def _handle_task_finished(self, task_id: str, result: object) -> None:
        if task_id not in self._states:
            return
        transcript_id = getattr(result, "id", None)
        state = self._states[task_id]
        status = TranscriptStatus.CANCELLED if self._tokens.get(task_id, CancellationToken()).is_cancelled else TranscriptStatus.COMPLETED
        updated = TranscriptJobState(
            job_id=state.job_id,
            video_id=state.video_id,
            model_name=state.model_name,
            status=status,
            progress_percent=100 if status == TranscriptStatus.COMPLETED else state.progress_percent,
            transcript_id=str(transcript_id) if transcript_id else None,
            error_message="" if status == TranscriptStatus.COMPLETED else "Cancelled",
        )
        self._states[task_id] = updated
        self._tokens.pop(task_id, None)
        self.job_finished.emit(updated)

    def _handle_task_failed(self, task_id: str, error: object) -> None:
        if task_id not in self._states:
            return
        state = self._states[task_id]
        status = TranscriptStatus.CANCELLED if isinstance(error, TranscriptionCancelled) else TranscriptStatus.FAILED
        updated = TranscriptJobState(
            job_id=state.job_id,
            video_id=state.video_id,
            model_name=state.model_name,
            status=status,
            progress_percent=state.progress_percent,
            transcript_id=state.transcript_id,
            error_message=str(error),
        )
        self._states[task_id] = updated
        self._tokens.pop(task_id, None)
        self.job_failed.emit(updated)
