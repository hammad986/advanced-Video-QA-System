from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class BackendStatus(str, Enum):
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    ERROR = "error"


@dataclass
class BackendState:
    status: BackendStatus = BackendStatus.STOPPED
    port: int | None = None
    base_url: str | None = None
    error_message: str | None = None

    @property
    def label(self) -> str:
        return self.status.value.title()
