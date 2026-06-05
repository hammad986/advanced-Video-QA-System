from __future__ import annotations

from PySide6.QtCore import QSettings

from desktop_app.core.app_constants import AppConstants
from desktop_app.core.events import EventBus
from desktop_app.main_window import MainWindow
from desktop_app.state.app_state import AppState


def _window(qapp, settings: QSettings) -> MainWindow:
    event_bus = EventBus()
    state = AppState(event_bus)
    window = MainWindow(state, event_bus, settings)
    window.resize(AppConstants.DEFAULT_WINDOW_WIDTH, AppConstants.DEFAULT_WINDOW_HEIGHT)
    window.show()
    qapp.processEvents()
    return window


def test_workspace_panels_resize_and_save(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "workspace.ini"), QSettings.Format.IniFormat)
    window = _window(qapp, settings)

    window.main_splitter.setSizes([340, 1100])
    window.top_splitter.setSizes([760, 300])
    window.work_splitter.setSizes([610, 260])
    qapp.processEvents()
    window.save_workspace_layout()

    assert int(settings.value(AppConstants.SETTINGS_KEY_LEFT_WIDTH)) > 0
    assert int(settings.value(AppConstants.SETTINGS_KEY_RIGHT_WIDTH)) > 0
    assert int(settings.value(AppConstants.SETTINGS_KEY_BOTTOM_HEIGHT)) > 0

    window.close()


def test_workspace_panels_collapse_and_restore(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "workspace.ini"), QSettings.Format.IniFormat)
    window = _window(qapp, settings)

    window.set_left_panel_visible(False)
    window.set_right_panel_visible(False)
    window.set_bottom_panel_visible(False)
    qapp.processEvents()

    assert window.main_splitter.sizes()[0] == 0
    assert window.top_splitter.sizes()[1] == 0
    assert window.work_splitter.sizes()[1] == 0
    assert window.left_region_action.isChecked() is False
    assert window.right_region_action.isChecked() is False
    assert window.bottom_region_action.isChecked() is False

    window.set_left_panel_visible(True)
    window.set_right_panel_visible(True)
    window.set_bottom_panel_visible(True)
    qapp.processEvents()

    assert window.main_splitter.sizes()[0] > 0
    assert window.top_splitter.sizes()[1] > 0
    assert window.work_splitter.sizes()[1] > 0
    assert window.left_region_action.isChecked() is True
    assert window.right_region_action.isChecked() is True
    assert window.bottom_region_action.isChecked() is True

    window.close()


def test_workspace_layout_persists_after_restart(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "workspace.ini"), QSettings.Format.IniFormat)
    first_window = _window(qapp, settings)

    first_window.apply_workspace_layout(left_width=315, right_width=285, bottom_height=245)
    first_window.save_window_settings()
    first_window.close()

    second_window = _window(qapp, settings)

    assert second_window.main_splitter.sizes()[0] > 250
    assert second_window.top_splitter.sizes()[1] > 200
    assert second_window.work_splitter.sizes()[1] > 180
    assert int(settings.value(AppConstants.SETTINGS_KEY_LEFT_WIDTH)) > 250
    assert int(settings.value(AppConstants.SETTINGS_KEY_RIGHT_WIDTH)) > 200
    assert int(settings.value(AppConstants.SETTINGS_KEY_BOTTOM_HEIGHT)) > 180

    second_window.close()


def test_workspace_splitter_directions_are_not_inverted(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "workspace.ini"), QSettings.Format.IniFormat)
    window = _window(qapp, settings)
    window.setFixedSize(1800, 1000)
    qapp.processEvents()

    window.apply_workspace_layout(left_width=260, right_width=240, bottom_height=180)
    qapp.processEvents()
    compact_left = window.main_splitter.sizes()[0]
    compact_right = window.top_splitter.sizes()[1]
    compact_bottom = window.work_splitter.sizes()[1]

    window.apply_workspace_layout(left_width=420, right_width=520, bottom_height=310)
    qapp.processEvents()

    assert window.main_splitter.sizes()[0] > compact_left
    assert window.top_splitter.sizes()[1] > compact_right
    assert window.work_splitter.sizes()[1] > compact_bottom

    window.close()


def test_workspace_reset_restores_default_dimensions(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "workspace.ini"), QSettings.Format.IniFormat)
    window = _window(qapp, settings)

    window.set_left_panel_visible(False)
    window.set_right_panel_visible(False)
    window.set_bottom_panel_visible(False)
    window.reset_workspace_layout()
    qapp.processEvents()

    assert window.main_splitter.sizes()[0] > 0
    assert window.top_splitter.sizes()[1] > 0
    assert window.work_splitter.sizes()[1] > 0
    assert window.left_region_action.isChecked() is True
    assert window.right_region_action.isChecked() is True
    assert window.bottom_region_action.isChecked() is True

    window.close()


def test_workspace_tabs_start_with_chat_and_plus_only(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "workspace.ini"), QSettings.Format.IniFormat)
    window = _window(qapp, settings)

    visible_titles = [window.ai_workspace_tabs.tabText(index) for index in range(window.ai_workspace_tabs.count())]

    assert visible_titles == ["Chat", "+"]
    assert window.ai_workspace_tabs.isMovable() is True
    assert window.ai_workspace_tabs.tabsClosable() is True

    window.open_workspace_tab("evidence")
    window.open_workspace_tab("diagnostics")
    visible_titles = [window.ai_workspace_tabs.tabText(index) for index in range(window.ai_workspace_tabs.count())]

    assert visible_titles == ["Chat", "Evidence", "Diagnostics", "+"]

    evidence_index = window.ai_workspace_tabs.indexOf(window.evidence_panel_widget)
    window.close_workspace_tab(evidence_index)
    visible_titles = [window.ai_workspace_tabs.tabText(index) for index in range(window.ai_workspace_tabs.count())]

    assert visible_titles == ["Chat", "Diagnostics", "+"]

    window.close()


def test_left_panel_accordion_supports_any_expanded_combination(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "workspace.ini"), QSettings.Format.IniFormat)
    window = _window(qapp, settings)

    assert [section.content.isVisible() for section in window.left_accordion_sections] == [False, False, False, False]

    window.set_left_accordion_section(window.left_accordion_sections[1])
    window.set_left_accordion_section(window.left_accordion_sections[2])
    expanded = [section.content.isVisible() for section in window.left_accordion_sections]

    assert expanded == [False, True, True, False]

    window.expand_all_left_accordion_sections()

    assert [section.content.isVisible() for section in window.left_accordion_sections] == [True, True, True, True]

    window.collapse_all_left_accordion_sections()

    assert [section.content.isVisible() for section in window.left_accordion_sections] == [False, False, False, False]

    window.close()
