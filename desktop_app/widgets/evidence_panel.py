from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from desktop_app.evidence.evidence_models import EvidenceItem, EvidenceJobState, EvidenceResult, EvidenceStatus
from desktop_app.transcript_viewer.transcript_navigation import format_timestamp


class EvidenceListModel(QAbstractListModel):
    PAGE_SIZE = 100

    def __init__(self) -> None:
        super().__init__()
        self.items: list[EvidenceItem] = []
        self.page = 0

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.visible_items())

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        items = self.visible_items()
        if not index.isValid() or not 0 <= index.row() < len(items):
            return None
        item = items[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            timestamp = f"{format_timestamp(item.start_time)} - {format_timestamp(item.end_time)}"
            return (
                f"#{item.retrieval_rank} · {item.source.video_name}\n"
                f"{item.topic_title} · [{timestamp}]\n"
                f"Similarity {item.similarity_score:.3f} · Confidence {item.confidence_score:.3f}\n"
                f"{item.chunk_text}"
            )
        if role == Qt.ItemDataRole.UserRole:
            return item
        return None

    def set_items(self, items: list[EvidenceItem]) -> None:
        self.beginResetModel()
        self.items = items
        self.page = 0
        self.endResetModel()

    def visible_items(self) -> list[EvidenceItem]:
        start = self.page * self.PAGE_SIZE
        return self.items[start : start + self.PAGE_SIZE]

    def page_count(self) -> int:
        if not self.items:
            return 1
        return ((len(self.items) - 1) // self.PAGE_SIZE) + 1

    def set_page(self, page: int) -> None:
        page = max(0, min(page, self.page_count() - 1))
        if page == self.page:
            return
        self.beginResetModel()
        self.page = page
        self.endResetModel()


class EvidencePanelWidget(QGroupBox):
    search_requested = Signal(str, int, float)
    evidence_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Evidence Panel", parent)
        self.status_label = QLabel("No evidence loaded")
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Search evidence candidates")
        self.top_k_input = QSpinBox()
        self.top_k_input.setRange(1, 10000)
        self.top_k_input.setValue(5)
        self.threshold_input = QDoubleSpinBox()
        self.threshold_input.setRange(0.0, 1.0)
        self.threshold_input.setSingleStep(0.05)
        self.threshold_input.setValue(0.0)
        self.search_button = QPushButton("Find Evidence")
        self.previous_page_button = QPushButton("Previous")
        self.next_page_button = QPushButton("Next")
        self.page_label = QLabel("Page 1 / 1")

        self.model = EvidenceListModel()
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.setUniformItemSizes(False)
        self.list_view.clicked.connect(self._emit_evidence_selected)

        search_row = QHBoxLayout()
        search_row.addWidget(self.query_input, 1)
        search_row.addWidget(QLabel("Top K"))
        search_row.addWidget(self.top_k_input)
        search_row.addWidget(QLabel("Min"))
        search_row.addWidget(self.threshold_input)
        search_row.addWidget(self.search_button)

        page_row = QHBoxLayout()
        page_row.addWidget(self.previous_page_button)
        page_row.addWidget(self.page_label)
        page_row.addWidget(self.next_page_button)
        page_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addLayout(search_row)
        layout.addWidget(self.list_view, 1)
        layout.addLayout(page_row)

        self.search_button.clicked.connect(self._emit_search)
        self.previous_page_button.clicked.connect(lambda: self._set_page(self.model.page - 1))
        self.next_page_button.clicked.connect(lambda: self._set_page(self.model.page + 1))
        self._update_pagination()

    def set_result(self, result: EvidenceResult) -> None:
        self.model.set_items(result.items)
        self.status_label.setText(f"{len(result.items):,} evidence candidates · {result.duration_ms:.1f} ms")
        self._update_pagination()

    def clear(self) -> None:
        self.model.set_items([])
        self.status_label.setText("No evidence loaded")
        self._update_pagination()

    def apply_state(self, state: EvidenceJobState) -> None:
        running = state.status in {EvidenceStatus.QUEUED, EvidenceStatus.RUNNING}
        self.search_button.setEnabled(not running)
        if state.status == EvidenceStatus.COMPLETED:
            self.status_label.setText(f"Evidence ready: {state.item_count:,} candidates")
        elif state.status == EvidenceStatus.FAILED:
            self.status_label.setText(f"Evidence failed: {state.error_message}")
        else:
            self.status_label.setText(f"Evidence {state.status.value}: {state.progress_percent}%")

    def _emit_search(self) -> None:
        query = self.query_input.text().strip()
        if not query:
            return
        self.search_requested.emit(query, int(self.top_k_input.value()), float(self.threshold_input.value()))

    def _emit_evidence_selected(self, index: QModelIndex) -> None:
        item = self.model.data(index, Qt.ItemDataRole.UserRole)
        if isinstance(item, EvidenceItem):
            self.evidence_selected.emit(item)

    def _set_page(self, page: int) -> None:
        self.model.set_page(page)
        self._update_pagination()

    def _update_pagination(self) -> None:
        page_count = self.model.page_count()
        self.page_label.setText(f"Page {self.model.page + 1} / {page_count}")
        self.previous_page_button.setEnabled(self.model.page > 0)
        self.next_page_button.setEnabled(self.model.page < page_count - 1)
