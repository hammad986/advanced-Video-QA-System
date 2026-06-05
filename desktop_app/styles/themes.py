from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemePalette:
    name: str
    background: str
    surface: str
    surface_alt: str
    border: str
    text: str
    muted_text: str
    accent: str
    success: str
    warning: str
    danger: str


DARK_THEME = ThemePalette(
    name="dark",
    background="#0b0f14",
    surface="#141b24",
    surface_alt="#0d1218",
    border="#263445",
    text="#e8edf2",
    muted_text="#8a96a3",
    accent="#4f9eff",
    success="#5fcf80",
    warning="#ffb454",
    danger="#ff6b6b",
)

LIGHT_THEME = ThemePalette(
    name="light",
    background="#f6f7f9",
    surface="#ffffff",
    surface_alt="#eef1f5",
    border="#d5dbe3",
    text="#17202a",
    muted_text="#617080",
    accent="#276ef1",
    success="#198754",
    warning="#a66700",
    danger="#c93434",
)


def build_stylesheet(palette: ThemePalette, font_family: str = "Segoe UI") -> str:
    return f"""
    QMainWindow, QWidget {{
        background: {palette.background};
        color: {palette.text};
        font-family: "{font_family}";
        font-size: 13px;
    }}

    QMenuBar {{
        background: {palette.surface};
        color: {palette.text};
        border-bottom: 1px solid {palette.border};
    }}

    QMenuBar::item:selected, QMenu::item:selected {{
        background: {palette.surface_alt};
    }}

    QMenu {{
        background: {palette.surface};
        color: {palette.text};
        border: 1px solid {palette.border};
    }}

    QStatusBar {{
        background: {palette.surface};
        color: {palette.muted_text};
        border-top: 1px solid {palette.border};
    }}

    QSplitter::handle {{
        background: {palette.border};
    }}

    QLabel#RegionTitle {{
        color: {palette.text};
        font-size: 15px;
        font-weight: 600;
    }}

    QLabel#RegionSubtitle {{
        color: {palette.muted_text};
    }}

    QWidget#RegionPlaceholder {{
        background: {palette.surface};
        border: 1px solid {palette.border};
        border-radius: 6px;
    }}
    """
