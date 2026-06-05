from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ThemeMode(str, Enum):
    DARK = "dark"
    LIGHT = "light"
    SYSTEM = "system"


@dataclass
class ThemeState:
    mode: ThemeMode = ThemeMode.DARK
    accent_color: str = "#4f9eff"
    resolved_mode: ThemeMode = ThemeMode.DARK

