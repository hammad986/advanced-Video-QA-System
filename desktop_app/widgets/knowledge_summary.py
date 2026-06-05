from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget

from desktop_app.knowledge.knowledge_models import KnowledgeChunk
from desktop_app.transcript_viewer.transcript_navigation import format_timestamp, seconds_to_milliseconds


class KnowledgeSummaryWidget(QWidget):
    generate_requested = Signal()
    chunk_selected = Signal(int)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.region_name = "knowledge-summary"
        self._chunks: list[KnowledgeChunk] = []

        self.title_label = QLabel("Knowledge Summary")
        self.status_label = QLabel("No knowledge chunks")
        self.generate_button = QPushButton("Generate Knowledge")
        self.chunk_list = QListWidget()
        self.chunk_list.itemClicked.connect(self._emit_selected_chunk)
        self.generate_button.clicked.connect(self.generate_requested.emit)

        header = QHBoxLayout()
        header.addWidget(self.title_label)
        header.addStretch(1)
        header.addWidget(self.generate_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(6)
        layout.addLayout(header)
        layout.addWidget(self.status_label)
        layout.addWidget(self.chunk_list, 1)

    def set_chunks(self, chunks: list[KnowledgeChunk]) -> None:
        self._chunks = chunks
        self.chunk_list.clear()
        for chunk in chunks:
            item = QListWidgetItem(self._label_for_chunk(chunk))
            item.setData(Qt.ItemDataRole.UserRole, seconds_to_milliseconds(chunk.start_time))
            self.chunk_list.addItem(item)
        self.status_label.setText(f"{len(chunks)} knowledge chunk{'s' if len(chunks) != 1 else ''}")

    def clear(self) -> None:
        self.set_chunks([])

    def _emit_selected_chunk(self, item: QListWidgetItem) -> None:
        self.chunk_selected.emit(int(item.data(Qt.ItemDataRole.UserRole)))

    def _label_for_chunk(self, chunk: KnowledgeChunk) -> str:
        timestamp = f"{format_timestamp(chunk.start_time)} - {format_timestamp(chunk.end_time)}"
        return f"{chunk.topic_title}\n[{timestamp}] · {chunk.word_count} words · {chunk.confidence:.2f}"
