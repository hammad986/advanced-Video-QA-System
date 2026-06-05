from __future__ import annotations

from desktop_app.backend.backend_manager import BackendManager
from desktop_app.backend.health_check import HealthCheckResult, HealthCheckSystem
from desktop_app.backend.lifecycle import BackendLifecycle
from desktop_app.backend.runtime_state import HealthStatus
from desktop_app.core.events import EventBus
from desktop_app.state.app_state import AppState
from desktop_app.state.backend_state import BackendStatus


def test_backend_manager_start_sets_running_when_health_is_healthy() -> None:
    state = AppState(EventBus())
    manager = BackendManager(
        state,
        health_check=HealthCheckSystem(lambda: HealthCheckResult.healthy("ready")),
    )

    snapshot = manager.start()

    assert snapshot.status == BackendStatus.RUNNING
    assert snapshot.health == HealthStatus.HEALTHY
    assert state.backend.status == BackendStatus.RUNNING


def test_backend_manager_stop_sets_stopped_and_degraded_health() -> None:
    state = AppState(EventBus())
    manager = BackendManager(
        state,
        health_check=HealthCheckSystem(lambda: HealthCheckResult.healthy("ready")),
    )
    manager.start()

    snapshot = manager.stop()

    assert snapshot.status == BackendStatus.STOPPED
    assert snapshot.health == HealthStatus.DEGRADED
    assert state.backend.status == BackendStatus.STOPPED


def test_backend_manager_startup_failure_sets_error() -> None:
    state = AppState(EventBus())
    lifecycle = BackendLifecycle()

    def fail() -> None:
        raise RuntimeError("startup failed")

    lifecycle.add_startup_step(fail)
    manager = BackendManager(state, lifecycle=lifecycle)

    snapshot = manager.start()

    assert snapshot.status == BackendStatus.ERROR
    assert snapshot.health == HealthStatus.FAILED
    assert snapshot.error_message == "startup failed"


def test_backend_manager_restart_runs_stop_then_start() -> None:
    state = AppState(EventBus())
    manager = BackendManager(
        state,
        health_check=HealthCheckSystem(lambda: HealthCheckResult.healthy("ready")),
    )

    snapshot = manager.restart()

    assert snapshot.status == BackendStatus.RUNNING
    assert snapshot.health == HealthStatus.HEALTHY

