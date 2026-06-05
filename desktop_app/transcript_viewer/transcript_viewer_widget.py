from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop_app.transcript_viewer.transcript_exporter import TranscriptExporter
from desktop_app.transcript_viewer.transcript_navigation import (
    find_active_segment_index,
    format_timestamp,
    seconds_to_milliseconds,
)
from desktop_app.transcript_viewer.transcript_search import TranscriptSearchEngine, TranscriptSearchResult
from desktop_app.transcripts.transcript_models import Transcript, TranscriptSegment


class TranscriptSegmentListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self.segments: list[TranscriptSegment] = []
        self.search_indices: set[int] = set()
        self.active_index: int | None = None

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.segments)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self.segments):
            return None
        segment = self.segments[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            timestamp = f"{format_timestamp(segment.start_time)} - {format_timestamp(segment.end_time)}"
            return f"[{timestamp}]  {segment.confidence:.2f}  {segment.text}"
        if role == Qt.ItemDataRole.UserRole:
            return seconds_to_milliseconds(segment.start_time)
        if role == Qt.ItemDataRole.BackgroundRole:
            if index.row() == self.active_index:
                return QColor("#27476a")
            if index.row() in self.search_indices:
                return QColor("#5a4a1f")
        return None

    def set_segments(self, segments: list[TranscriptSegment]) -> None:
        self.beginResetModel()
        self.segments = segments
        self.search_indices = set()
        self.active_index = None
        self.endResetModel()

    def set_search_indices(self, indices: list[int]) -> None:
        self.search_indices = set(indices)
        if self.segments:
            self.dataChanged.emit(self.index(0), self.index(len(self.segments) - 1))

    def set_active_index(self, index: int | None) -> None:
        previous = self.active_index
        self.active_index = index
        for row in (previous, index):
            if row is not None and 0 <= row < len(self.segments):
                model_index = self.index(row)
                self.dataChanged.emit(model_index, model_index)


class TranscriptViewerWidget(QWidget):
    segment_selected = Signal(int)
    export_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.region_name = "bottom"
        self.transcript: Transcript | None = None
        self.segments: list[TranscriptSegment] = []
        self.search_engine = TranscriptSearchEngine()
        self.search_result = TranscriptSearchResult(query="", indices=[])
        self.exporter = TranscriptExporter()

        self.title_label = QLabel("Transcript Viewer")
        self.status_label = QLabel("No transcript loaded")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search transcript")
        self.previous_button = QPushButton("Previous")
        self.next_button = QPushButton("Next")
        self.export_txt_button = QPushButton("Export TXT")
        self.export_markdown_button = QPushButton("Export Markdown")
        self.export_json_button = QPushButton("Export JSON")

        self.model = TranscriptSegmentListModel()
        self.segment_view = QListView()
        self.segment_view.setModel(self.model)
        self.segment_view.setUniformItemSizes(True)
        self.segment_view.clicked.connect(self._emit_segment_selected)

        search_row = QHBoxLayout()
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.previous_button)
        search_row.addWidget(self.next_button)

        export_row = QHBoxLayout()
        export_row.addWidget(self.export_txt_button)
        export_row.addWidget(self.export_markdown_button)
        export_row.addWidget(self.export_json_button)
        export_row.addStretch(1)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(6)
        layout.addWidget(self.title_label)
        layout.addWidget(self.status_label)
        layout.addLayout(search_row)
        layout.addWidget(self.segment_view, 1)
        layout.addLayout(export_row)

        self.search_input.textChanged.connect(self.apply_search)
        self.next_button.clicked.connect(self.next_result)
        self.previous_button.clicked.connect(self.previous_result)
        self.export_txt_button.clicked.connect(lambda: self.export_requested.emit("txt"))
        self.export_markdown_button.clicked.connect(lambda: self.export_requested.emit("md"))
        self.export_json_button.clicked.connect(lambda: self.export_requested.emit("json"))
        self._update_actions()

    def load_transcript(self, transcript: Transcript, segments: list[TranscriptSegment]) -> None:
        self.transcript = transcript
        self.segments = segments
        self.model.set_segments(segments)
        self.search_input.clear()
        self.search_result = TranscriptSearchResult(query="", indices=[])
        self.status_label.setText(
            f"{len(segments):,} segments · language {transcript.language or 'unknown'} · model {transcript.model_name}"
        )
        self._update_actions()

    def clear(self) -> None:
        self.transcript = None
        self.segments = []
        self.model.set_segments([])
        self.status_label.setText("No transcript loaded")
        self._update_actions()

    def apply_search(self, query: str) -> None:
        self.search_result = self.search_engine.search(self.segments, query)
        self.model.set_search_indices(self.search_result.indices)
        self._select_current_search_result()
        self._update_actions()

    def next_result(self) -> None:
        self.search_result = self.search_engine.next_result(self.search_result)
        self._select_current_search_result()

    def previous_result(self) -> None:
        self.search_result = self.search_engine.previous_result(self.search_result)
        self._select_current_search_result()

    def set_playback_position(self, position_ms: int) -> None:
        active_index = find_active_segment_index(self.segments, position_ms)
        if active_index == self.model.active_index:
            return
        self.model.set_active_index(active_index)
        if active_index is not None:
            self.segment_view.scrollTo(self.model.index(active_index), QListView.ScrollHint.PositionAtCenter)

    def export_current(self, format_name: str, output_dir: Path) -> Path:
        if self.transcript is None:
            raise ValueError("No transcript loaded.")
        stem = f"transcript_{self.transcript.video_id}"
        if format_name == "txt":
            return self.exporter.export_txt(self.transcript, self.segments, output_dir / f"{stem}.txt")
        if format_name == "md":
            return self.exporter.export_markdown(self.transcript, self.segments, output_dir / f"{stem}.md")
        if format_name == "json":
            return self.exporter.export_json(self.transcript, self.segments, output_dir / f"{stem}.json")
        raise ValueError(f"Unsupported transcript export format: {format_name}")

    def _emit_segment_selected(self, index: QModelIndex) -> None:
        value = self.model.data(index, Qt.ItemDataRole.UserRole)
        if value is not None:
            self.segment_selected.emit(int(value))

    def _select_current_search_result(self) -> None:
        current_index = self.search_result.current_index
        if current_index is None:
            return
        model_index = self.model.index(current_index)
        self.segment_view.setCurrentIndex(model_index)
        self.segment_view.scrollTo(model_index, QListView.ScrollHint.PositionAtCenter)

    def _update_actions(self) -> None:
        has_transcript = self.transcript is not None
        has_results = bool(self.search_result.indices)
        self.search_input.setEnabled(has_transcript)
        self.previous_button.setEnabled(has_results)
        self.next_button.setEnabled(has_results)
        self.export_txt_button.setEnabled(has_transcript)
        self.export_markdown_button.setEnabled(has_transcript)
        self.export_json_button.setEnabled(has_transcript)
