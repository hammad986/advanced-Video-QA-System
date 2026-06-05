from __future__ import annotations

import uuid

from PySide6.QtCore import QObject, Signal

from desktop_app.knowledge.knowledge_models import KnowledgeChunk
from desktop_app.knowledge.knowledge_service import KnowledgeService
from desktop_app.services.task_runner import TaskRunner


class KnowledgeManager(QObject):
    structuring_started = Signal(str)
    structuring_finished = Signal(str, object)
    structuring_failed = Signal(str, object)

    def __init__(self, knowledge_service: KnowledgeService, task_runner: TaskRunner) -> None:
        super().__init__()
        self.knowledge_service = knowledge_service
        self.task_runner = task_runner
        self._pending_tasks: set[str] = set()
        self.task_runner.signals.finished.connect(self._handle_task_finished)
        self.task_runner.signals.failed.connect(self._handle_task_failed)

    def structure_transcript_async(self, transcript_id: str) -> str:
        task_id = f"knowledge-{uuid.uuid4().hex}"

        def run() -> list[KnowledgeChunk]:
            return self.knowledge_service.structure_transcript(transcript_id)

        self._pending_tasks.add(task_id)
        self.structuring_started.emit(task_id)
        self.task_runner.run(run, task_id=task_id)
        return task_id

    def structure_transcript(self, transcript_id: str) -> list[KnowledgeChunk]:
        return self.knowledge_service.structure_transcript(transcript_id)

    def list_chunks(self, transcript_id: str) -> list[KnowledgeChunk]:
        return self.knowledge_service.list_chunks(transcript_id)

    def _handle_task_finished(self, task_id: str, result: object) -> None:
        if task_id not in self._pending_tasks:
            return
        self._pending_tasks.remove(task_id)
        self.structuring_finished.emit(task_id, result)

    def _handle_task_failed(self, task_id: str, error: object) -> None:
        if task_id not in self._pending_tasks:
            return
        self._pending_tasks.remove(task_id)
        self.structuring_failed.emit(task_id, error)
