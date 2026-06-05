from __future__ import annotations

import uuid

from PySide6.QtCore import QObject, Signal

from desktop_app.evidence.evidence_models import EvidenceJobState, EvidenceResult, EvidenceStatus
from desktop_app.evidence.evidence_service import EvidenceService
from desktop_app.services.task_runner import TaskRunner


class EvidenceManager(QObject):
    job_queued = Signal(object)
    progress_changed = Signal(object)
    job_finished = Signal(object)
    job_failed = Signal(object)

    def __init__(self, evidence_service: EvidenceService, task_runner: TaskRunner) -> None:
        super().__init__()
        self.evidence_service = evidence_service
        self.task_runner = task_runner
        self._jobs: dict[str, EvidenceJobState] = {}
        self.task_runner.signals.finished.connect(self._handle_task_finished)
        self.task_runner.signals.failed.connect(self._handle_task_failed)

    def generate_async(
        self,
        *,
        project_id: str,
        query: str,
        embedding_selection: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> str:
        job_id = f"evidence-{uuid.uuid4().hex}"
        state = EvidenceJobState(
            job_id=job_id,
            project_id=project_id,
            query=query,
            status=EvidenceStatus.QUEUED,
        )
        self._jobs[job_id] = state
        self.job_queued.emit(state)

        def run() -> EvidenceResult:
            self._set_state(job_id, EvidenceStatus.RUNNING, progress_percent=20)
            result = self.evidence_service.generate(
                project_id=project_id,
                query=query,
                embedding_selection=embedding_selection,
                top_k=top_k,
                min_similarity=min_similarity,
            )
            self._set_state(job_id, EvidenceStatus.RUNNING, progress_percent=90)
            return result

        self.task_runner.run(run, task_id=job_id)
        return job_id

    def _set_state(
        self,
        job_id: str,
        status: EvidenceStatus,
        *,
        progress_percent: int | None = None,
        item_count: int | None = None,
        duration_ms: float | None = None,
        error_message: str | None = None,
    ) -> None:
        old = self._jobs[job_id]
        state = EvidenceJobState(
            job_id=job_id,
            project_id=old.project_id,
            query=old.query,
            status=status,
            progress_percent=old.progress_percent if progress_percent is None else progress_percent,
            item_count=old.item_count if item_count is None else item_count,
            duration_ms=old.duration_ms if duration_ms is None else duration_ms,
            error_message=old.error_message if error_message is None else error_message,
        )
        self._jobs[job_id] = state
        self.progress_changed.emit(state)

    def _handle_task_finished(self, task_id: str, result: object) -> None:
        if task_id not in self._jobs:
            return
        evidence_result = result if isinstance(result, EvidenceResult) else None
        self._set_state(
            task_id,
            EvidenceStatus.COMPLETED,
            progress_percent=100,
            item_count=len(evidence_result.items) if evidence_result else 0,
            duration_ms=evidence_result.duration_ms if evidence_result else 0.0,
        )
        self.job_finished.emit(evidence_result if evidence_result else self._jobs[task_id])

    def _handle_task_failed(self, task_id: str, error: object) -> None:
        if task_id not in self._jobs:
            return
        self._set_state(
            task_id,
            EvidenceStatus.FAILED,
            error_message=str(error),
        )
        self.job_failed.emit(self._jobs[task_id])
