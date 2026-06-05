from __future__ import annotations

import uuid

from PySide6.QtCore import QObject, Signal

from desktop_app.compare.compare_models import CompareJobState, CompareResult, CompareStatus
from desktop_app.compare.compare_service import CompareService
from desktop_app.services.task_runner import TaskRunner


class CompareManager(QObject):
    job_queued = Signal(object)
    progress_changed = Signal(object)
    job_finished = Signal(object)
    job_failed = Signal(object)

    def __init__(self, compare_service: CompareService, task_runner: TaskRunner) -> None:
        super().__init__()
        self.compare_service = compare_service
        self.task_runner = task_runner
        self._jobs: dict[str, CompareJobState] = {}
        self.task_runner.signals.finished.connect(self._handle_task_finished)
        self.task_runner.signals.failed.connect(self._handle_task_failed)

    def compare_async(
        self,
        *,
        project_id: str,
        session_name: str,
        video_ids: list[str],
        query: str,
        embedding_selection: str,
        min_similarity: float = 0.0,
    ) -> str:
        job_id = f"compare-{uuid.uuid4().hex}"
        state = CompareJobState(job_id=job_id, project_id=project_id, query=query, status=CompareStatus.QUEUED)
        self._jobs[job_id] = state
        self.job_queued.emit(state)

        def run() -> CompareResult:
            self._set_state(job_id, CompareStatus.RUNNING, progress_percent=20)
            result = self.compare_service.compare(
                project_id=project_id,
                session_name=session_name,
                video_ids=video_ids,
                query=query,
                embedding_selection=embedding_selection,
                min_similarity=min_similarity,
            )
            finding_count = (
                len(result.agreements)
                + len(result.differences)
                + len(result.unique_concepts)
                + len(result.missing_topics)
                + len(result.contradictions)
                + len(result.timeline_differences)
            )
            self._set_state(
                job_id,
                CompareStatus.RUNNING,
                progress_percent=90,
                finding_count=finding_count,
                duration_ms=result.duration_ms,
            )
            return result

        self.task_runner.run(run, task_id=job_id)
        return job_id

    def _set_state(
        self,
        job_id: str,
        status: CompareStatus,
        *,
        progress_percent: int | None = None,
        finding_count: int | None = None,
        duration_ms: float | None = None,
        error_message: str | None = None,
    ) -> None:
        old = self._jobs[job_id]
        state = CompareJobState(
            job_id=job_id,
            project_id=old.project_id,
            query=old.query,
            status=status,
            progress_percent=old.progress_percent if progress_percent is None else progress_percent,
            finding_count=old.finding_count if finding_count is None else finding_count,
            duration_ms=old.duration_ms if duration_ms is None else duration_ms,
            error_message=old.error_message if error_message is None else error_message,
        )
        self._jobs[job_id] = state
        self.progress_changed.emit(state)

    def _handle_task_finished(self, task_id: str, result: object) -> None:
        if task_id not in self._jobs:
            return
        compare_result = result if isinstance(result, CompareResult) else None
        self._set_state(
            task_id,
            CompareStatus.COMPLETED,
            progress_percent=100,
            finding_count=self._finding_count(compare_result),
            duration_ms=compare_result.duration_ms if compare_result else 0.0,
        )
        self.job_finished.emit(compare_result if compare_result else self._jobs[task_id])

    def _handle_task_failed(self, task_id: str, error: object) -> None:
        if task_id not in self._jobs:
            return
        self._set_state(task_id, CompareStatus.FAILED, error_message=str(error))
        self.job_failed.emit(self._jobs[task_id])

    def _finding_count(self, result: CompareResult | None) -> int:
        if result is None:
            return 0
        return (
            len(result.agreements)
            + len(result.differences)
            + len(result.unique_concepts)
            + len(result.missing_topics)
            + len(result.contradictions)
            + len(result.timeline_differences)
        )
