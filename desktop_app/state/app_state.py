from __future__ import annotations

from PySide6.QtCore import QObject

from desktop_app.core.events import EventBus
from desktop_app.state.backend_state import BackendState, BackendStatus
from desktop_app.state.project_state import ProjectState
from desktop_app.state.theme_state import ThemeMode, ThemeState


class AppState(QObject):
    def __init__(self, event_bus: EventBus | None = None) -> None:
        super().__init__()
        self.event_bus = event_bus or EventBus()
        self.project = ProjectState()
        self.theme = ThemeState()
        self.backend = BackendState()

    def set_active_project(
        self,
        project_id: str | None,
        name: str,
        workspace_path: str | None = None,
    ) -> None:
        self.project.active_project_id = project_id
        self.project.active_project_name = name or "No Project"
        self.project.workspace_path = workspace_path
        self.project.is_dirty = False
        self.event_bus.state_changed.emit(self)

    def set_theme_mode(
        self,
        mode: ThemeMode,
        *,
        resolved_mode: ThemeMode | None = None,
        accent_color: str | None = None,
    ) -> None:
        self.theme.mode = mode
        self.theme.resolved_mode = resolved_mode or mode
        if accent_color:
            self.theme.accent_color = accent_color
        self.event_bus.theme_changed.emit(self.theme)
        self.event_bus.state_changed.emit(self)

    def set_backend_status(
        self,
        status: BackendStatus,
        *,
        port: int | None = None,
        base_url: str | None = None,
        error_message: str | None = None,
    ) -> None:
        self.backend.status = status
        self.backend.port = port
        self.backend.base_url = base_url
        self.backend.error_message = error_message
        self.event_bus.backend_status_changed.emit(self.backend)
        self.event_bus.state_changed.emit(self)

    def serialize_minimal(self) -> dict[str, object]:
        return {
            "project": {
                "active_project_id": self.project.active_project_id,
                "active_project_name": self.project.active_project_name,
                "workspace_path": self.project.workspace_path,
            },
            "theme": {
                "mode": self.theme.mode.value,
                "accent_color": self.theme.accent_color,
            },
            "backend": {
                "status": self.backend.status.value,
                "port": self.backend.port,
                "base_url": self.backend.base_url,
            },
        }

    def restore_minimal(self, payload: dict[str, object]) -> None:
        project = payload.get("project")
        if isinstance(project, dict):
            self.project.active_project_id = project.get("active_project_id")  # type: ignore[assignment]
            self.project.active_project_name = str(project.get("active_project_name") or "No Project")
            self.project.workspace_path = project.get("workspace_path")  # type: ignore[assignment]

        theme = payload.get("theme")
        if isinstance(theme, dict):
            mode_value = str(theme.get("mode") or ThemeMode.DARK.value)
            self.theme.mode = ThemeMode(mode_value)
            self.theme.resolved_mode = self.theme.mode
            self.theme.accent_color = str(theme.get("accent_color") or self.theme.accent_color)

        self.event_bus.state_changed.emit(self)
