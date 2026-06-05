from __future__ import annotations

from PySide6.QtCore import QSettings

from desktop_app.core.events import EventBus
from desktop_app.database.database_manager import DatabaseManager
from desktop_app.projects.project_manager import ProjectManager
from desktop_app.projects.project_models import ProjectStatus
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.state.app_state import AppState


def make_project_service(tmp_path) -> ProjectService:
    manager = DatabaseManager(tmp_path / "app.db")
    manager.initialize()
    repository = ProjectRepository(manager.connection)
    return ProjectService(repository)


def test_project_service_create_archive_restore_delete(tmp_path) -> None:
    service = make_project_service(tmp_path)
    project_root = tmp_path / "projects" / "Research A"

    project = service.create_project(
        name="Research A",
        description="A study project",
        root_path=str(project_root),
    )

    assert project.id
    assert project.status == ProjectStatus.ACTIVE
    assert project_root.exists()
    assert service.get_project(project.id) is not None

    archived = service.archive_project(project.id)
    assert archived is not None
    assert archived.status == ProjectStatus.ARCHIVED
    assert archived.archived_at is not None

    restored = service.restore_project(project.id)
    assert restored is not None
    assert restored.status == ProjectStatus.ACTIVE
    assert restored.archived_at is None

    assert service.delete_project(project.id) is True
    assert service.get_project(project.id) is None


def test_project_service_lists_active_projects_by_default(tmp_path) -> None:
    service = make_project_service(tmp_path)
    active = service.create_project(name="Active", root_path=str(tmp_path / "active"))
    archived = service.create_project(name="Archived", root_path=str(tmp_path / "archived"))
    service.archive_project(archived.id)

    active_projects = service.list_projects()
    all_projects = service.list_projects(include_archived=True)

    assert [project.id for project in active_projects] == [active.id]
    assert {project.id for project in all_projects} == {active.id, archived.id}


def test_project_manager_persists_and_restores_active_project(qapp, tmp_path) -> None:
    service = make_project_service(tmp_path)
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.Format.IniFormat)
    state = AppState(EventBus())
    manager = ProjectManager(state, service, settings)
    project = manager.create_project(
        name="Persistent Project",
        description="",
        root_path=str(tmp_path / "persistent"),
    )

    restored_state = AppState(EventBus())
    restored_manager = ProjectManager(restored_state, service, settings)
    restored = restored_manager.restore_last_active_project()

    assert restored is not None
    assert restored.id == project.id
    assert restored_state.project.active_project_id == project.id
    assert restored_state.project.active_project_name == "Persistent Project"

