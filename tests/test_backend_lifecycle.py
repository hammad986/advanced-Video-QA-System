from __future__ import annotations

from desktop_app.backend.lifecycle import BackendLifecycle


def test_lifecycle_runs_startup_in_registration_order() -> None:
    events: list[str] = []
    lifecycle = BackendLifecycle()
    lifecycle.add_startup_step(lambda: events.append("one"))
    lifecycle.add_startup_step(lambda: events.append("two"))

    lifecycle.startup()

    assert events == ["one", "two"]


def test_lifecycle_runs_shutdown_and_cleanup_in_reverse_order() -> None:
    events: list[str] = []
    lifecycle = BackendLifecycle()
    lifecycle.add_shutdown_step(lambda: events.append("shutdown-one"))
    lifecycle.add_shutdown_step(lambda: events.append("shutdown-two"))
    lifecycle.add_cleanup_step(lambda: events.append("cleanup-one"))
    lifecycle.add_cleanup_step(lambda: events.append("cleanup-two"))

    lifecycle.shutdown()
    lifecycle.cleanup()

    assert events == ["shutdown-two", "shutdown-one", "cleanup-two", "cleanup-one"]

