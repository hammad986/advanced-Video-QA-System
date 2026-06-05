from __future__ import annotations

from PySide6.QtCore import QSettings

from desktop_app.state.theme_state import ThemeMode, ThemeState
from desktop_app.styles.theme_manager import ThemeManager


def test_theme_manager_persists_theme(qapp, tmp_path) -> None:
    settings_path = tmp_path / "theme.ini"
    settings = QSettings(str(settings_path), QSettings.Format.IniFormat)
    manager = ThemeManager(qapp, settings)

    manager.apply_theme(ThemeState(mode=ThemeMode.LIGHT, accent_color="#123456"))
    loaded = manager.load_theme_preference()

    assert loaded.mode == ThemeMode.LIGHT
    assert loaded.accent_color == "#123456"
    assert "QMainWindow" in qapp.styleSheet()

