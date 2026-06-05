from __future__ import annotations

from PySide6.QtCore import QSettings

from desktop_app.core.events import EventBus
from desktop_app.database.database_manager import DatabaseManager
from desktop_app.main_window import MainWindow
from desktop_app.projects.project_manager import ProjectManager
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.state.app_state import AppState
from desktop_app.state.backend_state import BackendStatus


def test_main_window_has_required_regions(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    event_bus = EventBus()
    state = AppState(event_bus)

    window = MainWindow(state, event_bus, settings)

    assert window.menuBar() is not None
    assert window.statusBar() is not None
    assert window.left_region.region_name == "left"
    assert window.video_library_widget.region_name == "video-library"
    assert window.center_region.region_name == "center"
    assert window.right_region.region_name == "right"
    assert window.chat_workspace_widget.title() == "Research Chat"
    assert window.compare_workspace_widget.title() == "Multi-Video Compare"
    assert window.bookmark_panel_widget.title() == "Bookmarks"
    assert window.highlight_panel_widget.title() == "Highlights"
    assert window.vector_index_panel_widget.title() == "Vector Store"
    assert window.evidence_panel_widget.title() == "Evidence Panel"
    assert window.bottom_region.region_name == "bottom"
    assert window.windowTitle() == "Advanced Video QA Pro"

    window.close()


def test_right_workspace_uses_product_tabs(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    event_bus = EventBus()
    state = AppState(event_bus)
    window = MainWindow(state, event_bus, settings)

    tab_names = [window.ai_workspace_tabs.tabText(index) for index in range(window.ai_workspace_tabs.count())]

    assert tab_names == ["Chat", "+"]
    assert window.ai_workspace_tabs.tabsClosable() is True
    assert window.ai_workspace_tabs.isMovable() is True
    window.open_workspace_tab("evidence")
    tab_names = [window.ai_workspace_tabs.tabText(index) for index in range(window.ai_workspace_tabs.count())]
    assert tab_names == ["Chat", "Evidence", "+"]
    assert window.right_region.layout().indexOf(window.ai_workspace_tabs) >= 0
    assert window.right_region.layout().indexOf(window.knowledge_summary_widget) == -1
    assert window.right_region.layout().indexOf(window.embedding_panel_widget) == -1
    assert window.right_region.layout().indexOf(window.vector_index_panel_widget) == -1
    assert window.right_region.layout().indexOf(window.evidence_panel_widget) == -1
    assert window.empty_project_hint.isVisibleTo(window.right_region)

    window.close()


def test_left_workspace_accordion_sections_toggle_independently(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    event_bus = EventBus()
    state = AppState(event_bus)
    window = MainWindow(state, event_bus, settings)

    assert [section.toggle_button.text() for section in window.left_accordion_sections] == [
        "Projects",
        "Videos",
        "Transcript",
        "Queue",
    ]
    assert all(section.content.isHidden() for section in window.left_accordion_sections)

    window.set_left_accordion_section(window.left_accordion_sections[1])
    window.set_left_accordion_section(window.left_accordion_sections[3])

    assert window.left_accordion_sections[1].content.isHidden() is False
    assert window.left_accordion_sections[3].content.isHidden() is False
    assert window.left_accordion_sections[0].content.isHidden() is True

    window.expand_all_left_accordion_sections()

    assert all(not section.content.isHidden() for section in window.left_accordion_sections)

    window.collapse_all_left_accordion_sections()

    assert all(section.content.isHidden() for section in window.left_accordion_sections)

    window.close()


def test_chat_workspace_is_decluttered(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    event_bus = EventBus()
    state = AppState(event_bus)
    window = MainWindow(state, event_bus, settings)

    assert not hasattr(window.chat_workspace_widget, "top_k_input")
    assert not hasattr(window.chat_workspace_widget, "threshold_input")
    assert not hasattr(window.chat_workspace_widget, "chat_sidebar")
    assert not hasattr(window.chat_workspace_widget, "citation_viewer")
    assert window.chat_workspace_widget.question_input is not None
    assert window.chat_workspace_widget.ask_button.text() == "Send"
    assert window.chat_workspace_widget.thread_view is not None

    window.close()


def test_main_window_project_switcher_lists_projects(qapp, tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    service = ProjectService(ProjectRepository(database.connection))
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    event_bus = EventBus()
    state = AppState(event_bus)
    manager = ProjectManager(state, service, settings)
    project = service.create_project(name="Project One", root_path=str(tmp_path / "project-one"))

    window = MainWindow(
        state,
        event_bus,
        settings,
        project_manager=manager,
        default_projects_dir=tmp_path / "projects",
    )

    window.refresh_project_switcher()

    assert window.project_switcher.project_combo.findData(project.id) >= 0

    window.close()


def test_main_window_backend_status_label_updates(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    event_bus = EventBus()
    state = AppState(event_bus)
    window = MainWindow(state, event_bus, settings)

    state.set_backend_status(BackendStatus.STARTING)
    assert window.backend_status_label.text() == "Backend: Starting"

    state.set_backend_status(BackendStatus.RUNNING)
    assert window.backend_status_label.text() == "Backend: Running"

    state.set_backend_status(BackendStatus.STOPPED)
    assert window.backend_status_label.text() == "Backend: Stopped"

    state.set_backend_status(BackendStatus.ERROR, error_message="boom")
    assert window.backend_status_label.text() == "Backend: Error"

    window.close()
