from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from time import time

from desktop_app.backend.runtime_state import HealthStatus
from desktop_app.state.backend_state import BackendStatus


@dataclass(frozen=True)
class HealthCheckResult:
    status: HealthStatus
    message: str
    checked_at: float

    @classmethod
    def healthy(cls, message: str = "Backend runtime foundation is ready.") -> "HealthCheckResult":
        return cls(HealthStatus.HEALTHY, message, time())

    @classmethod
    def degraded(cls, message: str) -> "HealthCheckResult":
        return cls(HealthStatus.DEGRADED, message, time())

    @classmethod
    def failed(cls, message: str) -> "HealthCheckResult":
        return cls(HealthStatus.FAILED, message, time())


class HealthCheckSystem:
    def __init__(self, probe: Callable[[], HealthCheckResult] | None = None) -> None:
        self._probe = probe

    def check(self, backend_status: BackendStatus) -> HealthCheckResult:
        if backend_status == BackendStatus.ERROR:
            return HealthCheckResult.failed("Backend runtime is in an error state.")
        if backend_status == BackendStatus.STOPPED:
            return HealthCheckResult.degraded("Backend runtime is stopped.")
        if self._probe is not None:
            try:
                return self._probe()
            except Exception as exc:
                return HealthCheckResult.failed(str(exc))
        return HealthCheckResult.healthy()

