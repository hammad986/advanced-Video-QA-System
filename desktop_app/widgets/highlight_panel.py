from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListView,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop_app.highlights.highlight_models import Highlight, HighlightColor
from desktop_app.transcript_viewer.transcript_navigation import format_timestamp


class HighlightListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self.highlights: list[Highlight] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.highlights)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self.highlights):
            return None
        highlight = self.highlights[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return (
                f"{highlight.color.value} · {format_timestamp(highlight.timestamp)}\n"
                f"{highlight.highlighted_text[:160]}\n"
                f"{highlight.note}"
            )
        if role == Qt.ItemDataRole.UserRole:
            return highlight
        return None

    def set_highlights(self, highlights: list[Highlight]) -> None:
        self.beginResetModel()
        self.highlights = highlights
        self.endResetModel()


class HighlightPanelWidget(QGroupBox):
    highlight_transcript_requested = Signal(str, str, str)
    highlight_evidence_requested = Signal(str, str)
    delete_requested = Signal(str)
    highlight_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Highlights", parent)
        self.status_label = QLabel("No highlights")
        self.color_combo = QComboBox()
        for color in HighlightColor:
            self.color_combo.addItem(color.value.title(), color.value)
        self.selected_text_input = QPlainTextEdit()
        self.selected_text_input.setPlaceholderText("Selected transcript text or leave blank for active segment")
        self.selected_text_input.setMaximumHeight(64)
        self.note_input = QPlainTextEdit()
        self.note_input.setPlaceholderText("Notes")
        self.note_input.setMaximumHeight(64)
        self.highlight_transcript_button = QPushButton("Highlight Transcript")
        self.highlight_evidence_button = QPushButton("Highlight Evidence")
        self.delete_button = QPushButton("Delete")
        self.model = HighlightListModel()
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.clicked.connect(self._emit_selected)

        actions = QHBoxLayout()
        actions.addWidget(self.highlight_transcript_button)
        actions.addWidget(self.highlight_evidence_button)
        actions.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.color_combo)
        layout.addWidget(self.selected_text_input)
        layout.addWidget(self.note_input)
        layout.addLayout(actions)
        layout.addWidget(self.list_view, 1)

        self.highlight_transcript_button.clicked.connect(self._emit_highlight_transcript)
        self.highlight_evidence_button.clicked.connect(self._emit_highlight_evidence)
        self.delete_button.clicked.connect(self._emit_delete)

    def set_highlights(self, highlights: list[Highlight]) -> None:
        self.model.set_highlights(highlights)
        self.status_label.setText(f"{len(highlights):,} highlights")

    def selected_highlight(self) -> Highlight | None:
        value = self.model.data(self.list_view.currentIndex(), Qt.ItemDataRole.UserRole)
        return value if isinstance(value, Highlight) else None

    def _emit_highlight_transcript(self) -> None:
        self.highlight_transcript_requested.emit(
            str(self.color_combo.currentData()),
            self.selected_text_input.toPlainText().strip(),
            self.note_input.toPlainText().strip(),
        )

    def _emit_highlight_evidence(self) -> None:
        self.highlight_evidence_requested.emit(str(self.color_combo.currentData()), self.note_input.toPlainText().strip())

    def _emit_selected(self, index: QModelIndex) -> None:
        value = self.model.data(index, Qt.ItemDataRole.UserRole)
        if isinstance(value, Highlight):
            self.highlight_selected.emit(value)

    def _emit_delete(self) -> None:
        highlight = self.selected_highlight()
        if highlight is not None:
            self.delete_requested.emit(highlight.id)
