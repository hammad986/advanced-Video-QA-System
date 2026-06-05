from __future__ import annotations

from PySide6.QtCore import QSettings

from desktop_app.core.app_constants import AppConstants
from desktop_app.projects.project_models import ResearchProject
from desktop_app.projects.project_service import ProjectService
from desktop_app.state.app_state import AppState


class ProjectManager:
    def __init__(self, app_state: AppState, project_service: ProjectService, settings: QSettings) -> None:
        self.app_state = app_state
        self.project_service = project_service
        self.settings = settings

    def create_project(self, *, name: str, description: str, root_path: str) -> ResearchProject:
        project = self.project_service.create_project(
            name=name,
            description=description,
            root_path=root_path,
        )
        self.open_project(project.id)
        return project

    def open_project(self, project_id: str) -> ResearchProject:
        project = self.project_service.get_project(project_id)
        if project is None:
            raise ValueError(f"Project '{project_id}' was not found.")
        self.app_state.set_active_project(project.id, project.name, project.root_path)
        self.settings.setValue(AppConstants.SETTINGS_KEY_ACTIVE_PROJECT_ID, project.id)
        self.settings.sync()
        return project

    def archive_project(self, project_id: str) -> ResearchProject | None:
        project = self.project_service.archive_project(project_id)
        if self.app_state.project.active_project_id == project_id:
            self.clear_active_project()
        return project

    def restore_project(self, project_id: str) -> ResearchProject | None:
        return self.project_service.restore_project(project_id)

    def delete_project(self, project_id: str) -> bool:
        deleted = self.project_service.delete_project(project_id)
        if deleted and self.app_state.project.active_project_id == project_id:
            self.clear_active_project()
        return deleted

    def clear_active_project(self) -> None:
        self.app_state.set_active_project(None, "No Project", None)
        self.settings.remove(AppConstants.SETTINGS_KEY_ACTIVE_PROJECT_ID)
        self.settings.sync()

    def restore_last_active_project(self) -> ResearchProject | None:
        project_id = self.settings.value(AppConstants.SETTINGS_KEY_ACTIVE_PROJECT_ID)
        if not project_id:
            return None
        project = self.project_service.get_project(str(project_id))
        if project is None:
            self.clear_active_project()
            return None
        self.app_state.set_active_project(project.id, project.name, project.root_path)
        return project
