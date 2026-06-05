from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class RegionPlaceholder(QWidget):
    def __init__(self, title: str, subtitle: str, region_name: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.region_name = region_name
        self.setObjectName("RegionPlaceholder")

        title_label = QLabel(title)
        title_label.setObjectName("RegionTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("RegionSubtitle")
        subtitle_label.setWordWrap(True)
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(8)
        layout.addStretch(1)
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        layout.addStretch(1)
