from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from PySide6.QtCore import QObject, Signal


@dataclass(frozen=True)
class AppEvent:
    name: str
    payload: dict[str, Any]


class EventBus(QObject):
    app_started = Signal()
    app_closing = Signal()
    state_changed = Signal(object)
    theme_changed = Signal(object)
    backend_status_changed = Signal(object)
    task_started = Signal(str)
    task_finished = Signal(str, object)
    task_failed = Signal(str, object)
