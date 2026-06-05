from __future__ import annotations

from desktop_app.core.events import EventBus
from desktop_app.state.app_state import AppState
from desktop_app.state.backend_state import BackendStatus
from desktop_app.state.theme_state import ThemeMode


def test_app_state_defaults() -> None:
    state = AppState(EventBus())

    assert state.project.active_project_name == "No Project"
    assert state.theme.mode == ThemeMode.DARK
    assert state.backend.status == BackendStatus.STOPPED


def test_app_state_updates_theme_and_serializes() -> None:
    state = AppState(EventBus())

    state.set_theme_mode(ThemeMode.LIGHT, accent_color="#276ef1")

    payload = state.serialize_minimal()
    assert payload["theme"] == {"mode": "light", "accent_color": "#276ef1"}


def test_app_state_updates_backend_status() -> None:
    state = AppState(EventBus())

    state.set_backend_status(BackendStatus.STARTING, port=5123, base_url="http://127.0.0.1:5123")

    assert state.backend.status == BackendStatus.STARTING
    assert state.backend.port == 5123
    assert state.backend.base_url == "http://127.0.0.1:5123"

