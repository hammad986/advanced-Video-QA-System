from __future__ import annotations

import uuid

from PySide6.QtCore import QObject, Signal

from desktop_app.embeddings.embedding_models import EmbeddingJobState, EmbeddingRecord, EmbeddingStatus
from desktop_app.embeddings.embedding_service import EmbeddingService
from desktop_app.embeddings.embedding_worker import CancellationToken, EmbeddingCancelled
from desktop_app.services.task_runner import TaskRunner


class EmbeddingManager(QObject):
    job_queued = Signal(object)
    progress_changed = Signal(object)
    job_finished = Signal(object)
    job_failed = Signal(object)

    def __init__(self, embedding_service: EmbeddingService, task_runner: TaskRunner) -> None:
        super().__init__()
        self.embedding_service = embedding_service
        self.task_runner = task_runner
        self._jobs: dict[str, EmbeddingJobState] = {}
        self._tokens: dict[str, CancellationToken] = {}
        self.task_runner.signals.finished.connect(self._handle_task_finished)
        self.task_runner.signals.failed.connect(self._handle_task_failed)

    def generate_embeddings_async(self, transcript_id: str, model_name: str) -> str:
        job_id = f"embeddings-{uuid.uuid4().hex}"
        token = CancellationToken()
        state = EmbeddingJobState(
            job_id=job_id,
            transcript_id=transcript_id,
            model_name=model_name,
            status=EmbeddingStatus.QUEUED,
        )
        self._jobs[job_id] = state
        self._tokens[job_id] = token
        self.job_queued.emit(state)

        def run() -> list[EmbeddingRecord]:
            self._set_state(job_id, EmbeddingStatus.RUNNING, progress_percent=5)
            return self.embedding_service.generate_for_transcript(
                transcript_id,
                model_name,
                cancellation_token=token,
                progress_callback=lambda percent, _message: self._set_state(
                    job_id,
                    EmbeddingStatus.RUNNING,
                    progress_percent=percent,
                ),
            )

        self.task_runner.run(run, task_id=job_id)
        return job_id

    def cancel(self, job_id: str) -> None:
        token = self._tokens.get(job_id)
        if token is None:
            return
        token.cancel()
        self._set_state(job_id, EmbeddingStatus.CANCELLED)

    def retry(self, transcript_id: str, model_name: str) -> str:
        return self.generate_embeddings_async(transcript_id, model_name)

    def count_for_transcript(self, transcript_id: str, model_name: str) -> int:
        return self.embedding_service.count_for_transcript(transcript_id, model_name)

    def _set_state(
        self,
        job_id: str,
        status: EmbeddingStatus,
        *,
        progress_percent: int | None = None,
        record_count: int | None = None,
        error_message: str | None = None,
    ) -> None:
        old_state = self._jobs[job_id]
        state = EmbeddingJobState(
            job_id=job_id,
            transcript_id=old_state.transcript_id,
            model_name=old_state.model_name,
            status=status,
            progress_percent=old_state.progress_percent if progress_percent is None else progress_percent,
            record_count=old_state.record_count if record_count is None else record_count,
            error_message=old_state.error_message if error_message is None else error_message,
        )
        self._jobs[job_id] = state
        self.progress_changed.emit(state)

    def _handle_task_finished(self, task_id: str, result: object) -> None:
        if task_id not in self._jobs:
            return
        records = result if isinstance(result, list) else []
        self._set_state(
            task_id,
            EmbeddingStatus.COMPLETED,
            progress_percent=100,
            record_count=len(records),
        )
        self.job_finished.emit(self._jobs[task_id])
        self._tokens.pop(task_id, None)

    def _handle_task_failed(self, task_id: str, error: object) -> None:
        if task_id not in self._jobs:
            return
        status = EmbeddingStatus.CANCELLED if isinstance(error, EmbeddingCancelled) else EmbeddingStatus.FAILED
        self._set_state(
            task_id,
            status,
            error_message=str(error),
        )
        self.job_failed.emit(self._jobs[task_id])
        self._tokens.pop(task_id, None)
