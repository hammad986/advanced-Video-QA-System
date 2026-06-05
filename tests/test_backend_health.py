from __future__ import annotations

from desktop_app.backend.health_check import HealthCheckResult, HealthCheckSystem
from desktop_app.backend.runtime_state import HealthStatus
from desktop_app.state.backend_state import BackendStatus


def test_health_check_reports_stopped_as_degraded() -> None:
    health = HealthCheckSystem()

    result = health.check(BackendStatus.STOPPED)

    assert result.status == HealthStatus.DEGRADED
    assert "stopped" in result.message


def test_health_check_reports_error_as_failed() -> None:
    health = HealthCheckSystem()

    result = health.check(BackendStatus.ERROR)

    assert result.status == HealthStatus.FAILED


def test_health_check_uses_probe_for_running_state() -> None:
    health = HealthCheckSystem(lambda: HealthCheckResult.healthy("probe ok"))

    result = health.check(BackendStatus.RUNNING)

    assert result.status == HealthStatus.HEALTHY
    assert result.message == "probe ok"


def test_health_check_probe_failure_becomes_failed() -> None:
    def probe() -> HealthCheckResult:
        raise RuntimeError("probe failed")

    health = HealthCheckSystem(probe)

    result = health.check(BackendStatus.RUNNING)

    assert result.status == HealthStatus.FAILED
    assert result.message == "probe failed"

