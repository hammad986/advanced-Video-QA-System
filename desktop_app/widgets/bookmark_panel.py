from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop_app.bookmarks.bookmark_models import Bookmark
from desktop_app.transcript_viewer.transcript_navigation import format_timestamp


class BookmarkListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self.bookmarks: list[Bookmark] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.bookmarks)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self.bookmarks):
            return None
        bookmark = self.bookmarks[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return (
                f"{bookmark.title}\n"
                f"{bookmark.bookmark_type.value} · {format_timestamp(bookmark.timestamp)}\n"
                f"{bookmark.note or bookmark.source_text[:120]}"
            )
        if role == Qt.ItemDataRole.UserRole:
            return bookmark
        return None

    def set_bookmarks(self, bookmarks: list[Bookmark]) -> None:
        self.beginResetModel()
        self.bookmarks = bookmarks
        self.endResetModel()


class BookmarkPanelWidget(QGroupBox):
    bookmark_evidence_requested = Signal(str, str)
    bookmark_segment_requested = Signal(str, str)
    bookmark_timestamp_requested = Signal(str, str)
    delete_requested = Signal(str)
    bookmark_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Bookmarks", parent)
        self.status_label = QLabel("No bookmarks")
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Bookmark title")
        self.note_input = QPlainTextEdit()
        self.note_input.setPlaceholderText("Notes")
        self.note_input.setMaximumHeight(64)
        self.bookmark_evidence_button = QPushButton("Bookmark Evidence")
        self.bookmark_segment_button = QPushButton("Bookmark Segment")
        self.bookmark_timestamp_button = QPushButton("Bookmark Timestamp")
        self.delete_button = QPushButton("Delete")
        self.model = BookmarkListModel()
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.clicked.connect(self._emit_selected)

        actions = QHBoxLayout()
        actions.addWidget(self.bookmark_evidence_button)
        actions.addWidget(self.bookmark_segment_button)
        actions.addWidget(self.bookmark_timestamp_button)
        actions.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.title_input)
        layout.addWidget(self.note_input)
        layout.addLayout(actions)
        layout.addWidget(self.list_view, 1)

        self.bookmark_evidence_button.clicked.connect(self._emit_bookmark_evidence)
        self.bookmark_segment_button.clicked.connect(self._emit_bookmark_segment)
        self.bookmark_timestamp_button.clicked.connect(self._emit_bookmark_timestamp)
        self.delete_button.clicked.connect(self._emit_delete)

    def set_bookmarks(self, bookmarks: list[Bookmark]) -> None:
        self.model.set_bookmarks(bookmarks)
        self.status_label.setText(f"{len(bookmarks):,} bookmarks")

    def selected_bookmark(self) -> Bookmark | None:
        value = self.model.data(self.list_view.currentIndex(), Qt.ItemDataRole.UserRole)
        return value if isinstance(value, Bookmark) else None

    def _emit_bookmark_evidence(self) -> None:
        self.bookmark_evidence_requested.emit(self.title_input.text().strip(), self.note_input.toPlainText().strip())

    def _emit_bookmark_segment(self) -> None:
        self.bookmark_segment_requested.emit(self.title_input.text().strip(), self.note_input.toPlainText().strip())

    def _emit_bookmark_timestamp(self) -> None:
        self.bookmark_timestamp_requested.emit(self.title_input.text().strip(), self.note_input.toPlainText().strip())

    def _emit_selected(self, index: QModelIndex) -> None:
        value = self.model.data(index, Qt.ItemDataRole.UserRole)
        if isinstance(value, Bookmark):
            self.bookmark_selected.emit(value)

    def _emit_delete(self) -> None:
        bookmark = self.selected_bookmark()
        if bookmark is not None:
            self.delete_requested.emit(bookmark.id)
