from __future__ import annotations

import logging

from PySide6.QtCore import QObject

from desktop_app.backend.health_check import HealthCheckResult, HealthCheckSystem
from desktop_app.backend.lifecycle import BackendLifecycle
from desktop_app.backend.runtime_state import BackendRuntimeSnapshot, HealthStatus
from desktop_app.state.app_state import AppState
from desktop_app.state.backend_state import BackendStatus

logger = logging.getLogger(__name__)


class BackendManager(QObject):
    def __init__(
        self,
        app_state: AppState,
        health_check: HealthCheckSystem | None = None,
        lifecycle: BackendLifecycle | None = None,
    ) -> None:
        super().__init__()
        self.app_state = app_state
        self.health_check = health_check or HealthCheckSystem()
        self.lifecycle = lifecycle or BackendLifecycle()
        self._last_health = HealthCheckResult.degraded("Backend runtime has not started.")

    def start(self) -> BackendRuntimeSnapshot:
        logger.info("Starting backend runtime foundation")
        self.app_state.set_backend_status(BackendStatus.STARTING)
        try:
            self.lifecycle.startup()
            self.app_state.set_backend_status(BackendStatus.RUNNING)
            self._last_health = self.health_check.check(BackendStatus.RUNNING)
            if self._last_health.status == HealthStatus.FAILED:
                self.app_state.set_backend_status(
                    BackendStatus.ERROR,
                    error_message=self._last_health.message,
                )
        except Exception as exc:
            logger.exception("Backend runtime startup failed")
            self._last_health = HealthCheckResult.failed(str(exc))
            self.app_state.set_backend_status(BackendStatus.ERROR, error_message=str(exc))
        return self.status()

    def stop(self) -> BackendRuntimeSnapshot:
        logger.info("Stopping backend runtime foundation")
        try:
            self.lifecycle.shutdown()
            self.lifecycle.cleanup()
            self.app_state.set_backend_status(BackendStatus.STOPPED)
            self._last_health = self.health_check.check(BackendStatus.STOPPED)
        except Exception as exc:
            logger.exception("Backend runtime shutdown failed")
            self._last_health = HealthCheckResult.failed(str(exc))
            self.app_state.set_backend_status(BackendStatus.ERROR, error_message=str(exc))
        return self.status()

    def restart(self) -> BackendRuntimeSnapshot:
        logger.info("Restarting backend runtime foundation")
        self.stop()
        return self.start()

    def status(self) -> BackendRuntimeSnapshot:
        backend = self.app_state.backend
        return BackendRuntimeSnapshot(
            status=backend.status,
            health=self._last_health.status,
            message=self._last_health.message,
            port=backend.port,
            base_url=backend.base_url,
            error_message=backend.error_message,
            checked_at=self._last_health.checked_at,
        )

    def refresh_health(self) -> BackendRuntimeSnapshot:
        backend_status = self.app_state.backend.status
        self._last_health = self.health_check.check(backend_status)
        if self._last_health.status == HealthStatus.FAILED and backend_status != BackendStatus.STOPPED:
            self.app_state.set_backend_status(BackendStatus.ERROR, error_message=self._last_health.message)
        return self.status()

