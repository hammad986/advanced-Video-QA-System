from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from time import time

from desktop_app.state.backend_state import BackendStatus


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass(frozen=True)
class BackendRuntimeSnapshot:
    status: BackendStatus
    health: HealthStatus
    message: str
    port: int | None = None
    base_url: str | None = None
    error_message: str | None = None
    checked_at: float = 0.0

    @classmethod
    def stopped(cls) -> "BackendRuntimeSnapshot":
        return cls(
            status=BackendStatus.STOPPED,
            health=HealthStatus.DEGRADED,
            message="Backend runtime is stopped.",
            checked_at=time(),
        )

