from __future__ import annotations

import uuid

from PySide6.QtCore import QObject, Signal

from desktop_app.retrieval.retrieval_models import RetrievalJobState, RetrievalResult, RetrievalStatus
from desktop_app.retrieval.retrieval_service import RetrievalService
from desktop_app.services.task_runner import TaskRunner


class RetrievalManager(QObject):
    job_queued = Signal(object)
    progress_changed = Signal(object)
    job_finished = Signal(object)
    job_failed = Signal(object)

    def __init__(self, retrieval_service: RetrievalService, task_runner: TaskRunner) -> None:
        super().__init__()
        self.retrieval_service = retrieval_service
        self.task_runner = task_runner
        self._jobs: dict[str, RetrievalJobState] = {}
        self.task_runner.signals.finished.connect(self._handle_task_finished)
        self.task_runner.signals.failed.connect(self._handle_task_failed)

    def search_async(
        self,
        *,
        project_id: str,
        query: str,
        embedding_selection: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> str:
        job_id = f"retrieval-{uuid.uuid4().hex}"
        state = RetrievalJobState(
            job_id=job_id,
            project_id=project_id,
            query=query,
            status=RetrievalStatus.QUEUED,
        )
        self._jobs[job_id] = state
        self.job_queued.emit(state)

        def run() -> RetrievalResult:
            self._set_state(job_id, RetrievalStatus.RUNNING, progress_percent=20)
            result = self.retrieval_service.search(
                project_id=project_id,
                query=query,
                embedding_selection=embedding_selection,
                top_k=top_k,
                min_similarity=min_similarity,
            )
            self._set_state(job_id, RetrievalStatus.RUNNING, progress_percent=90)
            return result

        self.task_runner.run(run, task_id=job_id)
        return job_id

    def _set_state(
        self,
        job_id: str,
        status: RetrievalStatus,
        *,
        progress_percent: int | None = None,
        hit_count: int | None = None,
        duration_ms: float | None = None,
        error_message: str | None = None,
    ) -> None:
        old = self._jobs[job_id]
        state = RetrievalJobState(
            job_id=job_id,
            project_id=old.project_id,
            query=old.query,
            status=status,
            progress_percent=old.progress_percent if progress_percent is None else progress_percent,
            hit_count=old.hit_count if hit_count is None else hit_count,
            duration_ms=old.duration_ms if duration_ms is None else duration_ms,
            error_message=old.error_message if error_message is None else error_message,
        )
        self._jobs[job_id] = state
        self.progress_changed.emit(state)

    def _handle_task_finished(self, task_id: str, result: object) -> None:
        if task_id not in self._jobs:
            return
        retrieval_result = result if isinstance(result, RetrievalResult) else None
        self._set_state(
            task_id,
            RetrievalStatus.COMPLETED,
            progress_percent=100,
            hit_count=len(retrieval_result.hits) if retrieval_result else 0,
            duration_ms=retrieval_result.duration_ms if retrieval_result else 0.0,
        )
        self.job_finished.emit(self._jobs[task_id])

    def _handle_task_failed(self, task_id: str, error: object) -> None:
        if task_id not in self._jobs:
            return
        self._set_state(
            task_id,
            RetrievalStatus.FAILED,
            error_message=str(error),
        )
        self.job_failed.emit(self._jobs[task_id])
