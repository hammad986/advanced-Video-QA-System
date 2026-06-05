from __future__ import annotations

import os
import sys
from pathlib import Path


def _bootstrap_import_path() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def main() -> int:
    _bootstrap_import_path()
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    os.environ.setdefault("ADVANCED_VIDEO_QA_SKIP_FIRST_RUN", "1")

    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QApplication

    from desktop_app.core.app_constants import AppConstants
    from desktop_app.core.app_paths import AppPaths
    from desktop_app.core.events import EventBus
    from desktop_app.core.logging_config import configure_logging
    from desktop_app.database.database_manager import DatabaseManager
    from desktop_app.main_window import MainWindow
    from desktop_app.providers.provider_manager import ProviderManager
    from desktop_app.projects.project_manager import ProjectManager
    from desktop_app.projects.project_repository import ProjectRepository
    from desktop_app.projects.project_service import ProjectService
    from desktop_app.settings.settings_manager import SettingsManager
    from desktop_app.settings.settings_repository import SettingsRepository
    from desktop_app.state.app_state import AppState
    from desktop_app.styles.theme_manager import ThemeManager

    paths = AppPaths.resolve()
    configure_logging(paths)
    paths.ensure()

    qt_app = QApplication(sys.argv)
    qt_app.setOrganizationName(AppConstants.ORGANIZATION_NAME)
    qt_app.setApplicationName(AppConstants.APPLICATION_NAME)
    qt_app.setApplicationVersion(AppConstants.APPLICATION_VERSION)

    settings = QSettings(AppConstants.ORGANIZATION_NAME, AppConstants.APPLICATION_NAME)
    event_bus = EventBus()
    state = AppState(event_bus)
    theme_manager = ThemeManager(qt_app, settings)
    event_bus.theme_changed.connect(theme_manager.apply_theme)
    state.set_theme_mode(theme_manager.load_theme_preference().mode)

    database = DatabaseManager(paths.database_path)
    database.initialize()
    settings_manager = SettingsManager(SettingsRepository(database.connection), default_workspace_path=paths.projects_dir)
    project_service = ProjectService(ProjectRepository(database.connection))
    project_manager = ProjectManager(state, project_service, settings)
    project_manager.restore_last_active_project()
    provider_manager = ProviderManager(database.connection, settings_manager)

    window = MainWindow(
        state,
        event_bus,
        settings,
        project_manager=project_manager,
        default_projects_dir=paths.projects_dir,
        settings_manager=settings_manager,
        provider_manager=provider_manager,
    )
    window.show()
    return qt_app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
