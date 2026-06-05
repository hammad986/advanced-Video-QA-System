from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtCore import QObject, QSettings
from PySide6.QtGui import QFont, QFontDatabase, QGuiApplication
from PySide6.QtWidgets import QApplication

from desktop_app.core.app_constants import AppConstants
from desktop_app.core.errors import ThemeError
from desktop_app.state.theme_state import ThemeMode, ThemeState
from desktop_app.styles.themes import DARK_THEME, LIGHT_THEME, build_stylesheet

logger = logging.getLogger(__name__)


class ThemeManager(QObject):
    def __init__(self, app: QApplication, settings: QSettings | None = None) -> None:
        super().__init__()
        self.app = app
        self.settings = settings or QSettings(AppConstants.ORGANIZATION_NAME, AppConstants.APPLICATION_NAME)
        self.font_family = self.load_application_font()
        self.app.setFont(QFont(self.font_family, 10))

    def load_theme_preference(self) -> ThemeState:
        mode_value = self.settings.value(AppConstants.SETTINGS_KEY_THEME_MODE, ThemeMode.DARK.value)
        accent = self.settings.value(AppConstants.SETTINGS_KEY_ACCENT_COLOR, DARK_THEME.accent)
        try:
            mode = ThemeMode(str(mode_value))
        except ValueError:
            logger.warning("Invalid persisted theme mode %r; using dark", mode_value)
            mode = ThemeMode.DARK
        resolved = self.resolve_system_theme() if mode == ThemeMode.SYSTEM else mode
        return ThemeState(mode=mode, accent_color=str(accent), resolved_mode=resolved)

    def save_theme_preference(self, theme_state: ThemeState) -> None:
        self.settings.setValue(AppConstants.SETTINGS_KEY_THEME_MODE, theme_state.mode.value)
        self.settings.setValue(AppConstants.SETTINGS_KEY_ACCENT_COLOR, theme_state.accent_color)
        self.settings.sync()

    def resolve_system_theme(self) -> ThemeMode:
        palette = QGuiApplication.palette()
        window_color = palette.window().color()
        brightness = (window_color.red() * 0.299) + (window_color.green() * 0.587) + (window_color.blue() * 0.114)
        return ThemeMode.DARK if brightness < 128 else ThemeMode.LIGHT

    def apply_theme(self, theme_state: ThemeState) -> None:
        resolved = self.resolve_system_theme() if theme_state.mode == ThemeMode.SYSTEM else theme_state.mode
        theme_state.resolved_mode = resolved
        palette = DARK_THEME if resolved == ThemeMode.DARK else LIGHT_THEME
        try:
            self.app.setStyleSheet(build_stylesheet(palette, self.font_family))
            self.save_theme_preference(theme_state)
        except Exception as exc:
            raise ThemeError("Could not apply theme.", str(exc)) from exc

    def load_application_font(self) -> str:
        if sys.platform != "win32":
            return self.app.font().family() or "Sans Serif"

        candidates = (
            Path("C:/Windows/Fonts/segoeui.ttf"),
            Path("C:/Windows/Fonts/arial.ttf"),
        )
        for font_path in candidates:
            if not font_path.exists():
                continue
            font_id = QFontDatabase.addApplicationFont(str(font_path))
            if font_id < 0:
                continue
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                return families[0]

        fallback = self.app.font().family()
        return fallback if fallback else "Sans Serif"
