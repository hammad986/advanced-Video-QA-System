from __future__ import annotations

import uuid
from collections.abc import Callable
from typing import Any

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot


class TaskSignals(QObject):
    started = Signal(str)
    finished = Signal(str, object)
    failed = Signal(str, object)
    progress = Signal(str, int, str)


class BackgroundTask(QRunnable):
    def __init__(self, task_id: str, callback: Callable[[], Any], signals: TaskSignals) -> None:
        super().__init__()
        self.task_id = task_id
        self.callback = callback
        self.signals = signals

    @Slot()
    def run(self) -> None:
        self.signals.started.emit(self.task_id)
        try:
            result = self.callback()
        except Exception as exc:
            self.signals.failed.emit(self.task_id, exc)
            return
        self.signals.finished.emit(self.task_id, result)


class TaskRunner(QObject):
    def __init__(self, thread_pool: QThreadPool | None = None) -> None:
        super().__init__()
        self.thread_pool = thread_pool or QThreadPool.globalInstance()
        self.signals = TaskSignals()

    def run(self, callback: Callable[[], Any], task_id: str | None = None) -> str:
        resolved_task_id = task_id or uuid.uuid4().hex
        task = BackgroundTask(resolved_task_id, callback, self.signals)
        self.thread_pool.start(task)
        return resolved_task_id

    def cancel(self, task_id: str) -> None:
        # Cancellation is reserved for future cooperative tasks.
        _ = task_id

    def shutdown(self) -> None:
        self.thread_pool.waitForDone(3000)
