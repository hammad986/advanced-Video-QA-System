from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from desktop_app.services.task_runner import TaskRunner
from desktop_app.vector_store.vector_repository import VectorIndexRecord
from desktop_app.vector_store.vector_service import VectorBuildResult, VectorService


class VectorIndexStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(frozen=True)
class VectorIndexJobState:
    job_id: str
    project_id: str
    embedding_selection: str
    status: VectorIndexStatus
    progress_percent: int = 0
    vector_count: int = 0
    index_path: str = ""
    error_message: str = ""


class VectorManager(QObject):
    job_queued = Signal(object)
    progress_changed = Signal(object)
    job_finished = Signal(object)
    job_failed = Signal(object)

    def __init__(self, vector_service: VectorService, task_runner: TaskRunner) -> None:
        super().__init__()
        self.vector_service = vector_service
        self.task_runner = task_runner
        self._jobs: dict[str, VectorIndexJobState] = {}
        self.task_runner.signals.finished.connect(self._handle_task_finished)
        self.task_runner.signals.failed.connect(self._handle_task_failed)

    def build_index_async(self, *, project_id: str, project_workspace: Path, embedding_selection: str) -> str:
        job_id = f"vector-{uuid.uuid4().hex}"
        state = VectorIndexJobState(
            job_id=job_id,
            project_id=project_id,
            embedding_selection=embedding_selection,
            status=VectorIndexStatus.QUEUED,
        )
        self._jobs[job_id] = state
        self.job_queued.emit(state)

        def run() -> VectorBuildResult:
            self._set_state(job_id, VectorIndexStatus.RUNNING, progress_percent=10)
            result = self.vector_service.build_project_index(
                project_id=project_id,
                project_workspace=project_workspace,
                embedding_selection=embedding_selection,
            )
            self._set_state(job_id, VectorIndexStatus.RUNNING, progress_percent=90)
            return result

        self.task_runner.run(run, task_id=job_id)
        return job_id

    def latest_index(self, project_id: str, embedding_selection: str) -> VectorIndexRecord | None:
        return self.vector_service.latest_index(project_id, embedding_selection)

    def _set_state(
        self,
        job_id: str,
        status: VectorIndexStatus,
        *,
        progress_percent: int | None = None,
        vector_count: int | None = None,
        index_path: str | None = None,
        error_message: str | None = None,
    ) -> None:
        old_state = self._jobs[job_id]
        state = VectorIndexJobState(
            job_id=job_id,
            project_id=old_state.project_id,
            embedding_selection=old_state.embedding_selection,
            status=status,
            progress_percent=old_state.progress_percent if progress_percent is None else progress_percent,
            vector_count=old_state.vector_count if vector_count is None else vector_count,
            index_path=old_state.index_path if index_path is None else index_path,
            error_message=old_state.error_message if error_message is None else error_message,
        )
        self._jobs[job_id] = state
        self.progress_changed.emit(state)

    def _handle_task_finished(self, task_id: str, result: object) -> None:
        if task_id not in self._jobs:
            return
        build_result = result if isinstance(result, VectorBuildResult) else None
        self._set_state(
            task_id,
            VectorIndexStatus.COMPLETED,
            progress_percent=100,
            vector_count=build_result.vector_count if build_result else 0,
            index_path=build_result.record.index_path if build_result else "",
        )
        self.job_finished.emit(self._jobs[task_id])

    def _handle_task_failed(self, task_id: str, error: object) -> None:
        if task_id not in self._jobs:
            return
        self._set_state(
            task_id,
            VectorIndexStatus.FAILED,
            error_message=str(error),
        )
        self.job_failed.emit(self._jobs[task_id])
