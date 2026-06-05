from __future__ import annotations

import uuid
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from desktop_app.services.task_runner import TaskRunner
from desktop_app.videos.video_model import VideoRecord
from desktop_app.videos.video_service import VideoService


class VideoManager(QObject):
    import_started = Signal(str)
    import_finished = Signal(str, object)
    import_failed = Signal(str, object)

    def __init__(self, video_service: VideoService, task_runner: TaskRunner) -> None:
        super().__init__()
        self.video_service = video_service
        self.task_runner = task_runner
        self._pending_import_tasks: set[str] = set()
        self.task_runner.signals.finished.connect(self._handle_task_finished)
        self.task_runner.signals.failed.connect(self._handle_task_failed)

    def import_videos_async(self, project_id: str, source_paths: list[str | Path]) -> str:
        def run_import() -> list[VideoRecord]:
            return self.video_service.import_videos(project_id, source_paths)

        task_id = self.task_runner.run(run_import, task_id=f"video-import-{uuid.uuid4().hex}")
        self._pending_import_tasks.add(task_id)
        self.import_started.emit(task_id)
        return task_id

    def list_project_videos(self, project_id: str, *, search: str = "") -> list[VideoRecord]:
        return self.video_service.list_project_videos(project_id, search=search)

    def get_video(self, video_id: str) -> VideoRecord | None:
        return self.video_service.get_video(video_id)

    def remove_video(self, video_id: str) -> bool:
        return self.video_service.remove_video(video_id)

    def _handle_task_finished(self, task_id: str, result: object) -> None:
        if task_id not in self._pending_import_tasks:
            return
        self._pending_import_tasks.remove(task_id)
        self.import_finished.emit(task_id, result)

    def _handle_task_failed(self, task_id: str, error: object) -> None:
        if task_id not in self._pending_import_tasks:
            return
        self._pending_import_tasks.remove(task_id)
        self.import_failed.emit(task_id, error)
