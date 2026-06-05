from __future__ import annotations

import uuid

from PySide6.QtCore import QObject, Signal

from desktop_app.chat.chat_models import ChatJobState, ChatJobStatus, ChatMessage
from desktop_app.chat.chat_service import ChatService
from desktop_app.services.task_runner import TaskRunner


class ChatManager(QObject):
    job_queued = Signal(object)
    progress_changed = Signal(object)
    message_finished = Signal(object)
    job_failed = Signal(object)

    def __init__(self, chat_service: ChatService, task_runner: TaskRunner) -> None:
        super().__init__()
        self.chat_service = chat_service
        self.task_runner = task_runner
        self._jobs: dict[str, ChatJobState] = {}
        self.task_runner.signals.finished.connect(self._handle_task_finished)
        self.task_runner.signals.failed.connect(self._handle_task_failed)

    def ask_async(
        self,
        *,
        session_id: str,
        project_id: str,
        question: str,
        embedding_selection: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> str:
        job_id = f"chat-{uuid.uuid4().hex}"
        state = ChatJobState(
            job_id=job_id,
            session_id=session_id,
            project_id=project_id,
            question=question,
            status=ChatJobStatus.QUEUED,
        )
        self._jobs[job_id] = state
        self.job_queued.emit(state)

        def run() -> ChatMessage:
            self._set_state(job_id, ChatJobStatus.RUNNING, progress_percent=20)
            message = self.chat_service.ask(
                session_id=session_id,
                project_id=project_id,
                question=question,
                embedding_selection=embedding_selection,
                top_k=top_k,
                min_similarity=min_similarity,
            )
            self._set_state(
                job_id,
                ChatJobStatus.RUNNING,
                progress_percent=90,
                provider=message.provider,
                duration_ms=message.duration_ms,
            )
            return message

        self.task_runner.run(run, task_id=job_id)
        return job_id

    def _set_state(
        self,
        job_id: str,
        status: ChatJobStatus,
        *,
        progress_percent: int | None = None,
        provider: str | None = None,
        duration_ms: float | None = None,
        error_message: str | None = None,
    ) -> None:
        old = self._jobs[job_id]
        state = ChatJobState(
            job_id=job_id,
            session_id=old.session_id,
            project_id=old.project_id,
            question=old.question,
            status=status,
            progress_percent=old.progress_percent if progress_percent is None else progress_percent,
            provider=old.provider if provider is None else provider,
            duration_ms=old.duration_ms if duration_ms is None else duration_ms,
            error_message=old.error_message if error_message is None else error_message,
        )
        self._jobs[job_id] = state
        self.progress_changed.emit(state)

    def _handle_task_finished(self, task_id: str, result: object) -> None:
        if task_id not in self._jobs:
            return
        message = result if isinstance(result, ChatMessage) else None
        self._set_state(
            task_id,
            ChatJobStatus.COMPLETED,
            progress_percent=100,
            provider=message.provider if message else "",
            duration_ms=message.duration_ms if message else 0.0,
        )
        self.message_finished.emit(message if message else self._jobs[task_id])

    def _handle_task_failed(self, task_id: str, error: object) -> None:
        if task_id not in self._jobs:
            return
        self._set_state(task_id, ChatJobStatus.FAILED, error_message=str(error))
        self.job_failed.emit(self._jobs[task_id])
