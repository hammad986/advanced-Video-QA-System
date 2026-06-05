from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import QLabel, QListView, QVBoxLayout, QWidget

from desktop_app.answering.answer_models import Citation
from desktop_app.transcript_viewer.transcript_navigation import format_timestamp


class CitationListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self.citations: list[Citation] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.citations)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self.citations):
            return None
        citation = self.citations[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            start = format_timestamp(citation.timestamp_start)
            end = format_timestamp(citation.timestamp_end)
            return (
                f"[{citation.citation_id}] {citation.source_video}\n"
                f"{start} - {end} · confidence {citation.confidence:.3f}\n"
                f"chunk {citation.chunk_id}"
            )
        if role == Qt.ItemDataRole.UserRole:
            return citation
        return None

    def set_citations(self, citations: list[Citation]) -> None:
        self.beginResetModel()
        self.citations = citations
        self.endResetModel()


class CitationViewerWidget(QWidget):
    citation_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.title_label = QLabel("Citations")
        self.status_label = QLabel("No citations selected")
        self.model = CitationListModel()
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.clicked.connect(self._emit_selected)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)
        layout.addWidget(self.list_view, 1)

    def set_citations(self, citations: list[Citation]) -> None:
        self.model.set_citations(citations)
        self.status_label.setText(f"{len(citations):,} citations")

    def clear(self) -> None:
        self.set_citations([])
        self.status_label.setText("No citations selected")

    def _emit_selected(self, index: QModelIndex) -> None:
        citation = self.model.data(index, Qt.ItemDataRole.UserRole)
        if isinstance(citation, Citation):
            self.citation_selected.emit(citation)
