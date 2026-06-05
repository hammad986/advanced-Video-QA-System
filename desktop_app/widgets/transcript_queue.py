from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressBar,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop_app.transcripts.transcript_models import (
    TranscriptJobState,
    TranscriptModelName,
    TranscriptStatus,
)


class TranscriptQueueWidget(QWidget):
    generate_requested = Signal(str)
    cancel_requested = Signal(str)
    retry_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.region_name = "transcript-queue"
        self._jobs: dict[str, TranscriptJobState] = {}

        self.title_label = QLabel("Transcript Processing")
        self.model_combo = QComboBox()
        for model in TranscriptModelName:
            self.model_combo.addItem(model.value, model.value)
        self.model_combo.setCurrentIndex(1)

        self.generate_button = QPushButton("Generate Transcript")
        self.cancel_button = QPushButton("Cancel")
        self.retry_button = QPushButton("Retry")
        self.status_label = QLabel("Transcript Status: Idle")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.queue_list = QListWidget()
        self.queue_list.currentRowChanged.connect(lambda _: self._update_actions())

        self.generate_button.clicked.connect(lambda: self.generate_requested.emit(self.current_model_name()))
        self.cancel_button.clicked.connect(self._emit_cancel)
        self.retry_button.clicked.connect(self._emit_retry)

        model_row = QHBoxLayout()
        model_row.addWidget(QLabel("Model"))
        model_row.addWidget(self.model_combo, 1)

        button_row = QHBoxLayout()
        button_row.addWidget(self.generate_button)
        button_row.addWidget(self.cancel_button)
        button_row.addWidget(self.retry_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(6)
        layout.addWidget(self.title_label)
        layout.addLayout(model_row)
        layout.addLayout(button_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(QLabel("Processing Queue"))
        layout.addWidget(self.queue_list, 1)
        self._update_actions()

    def current_model_name(self) -> str:
        return str(self.model_combo.currentData())

    def set_transcript_enabled(self, enabled: bool) -> None:
        self.generate_button.setEnabled(enabled)
        self.model_combo.setEnabled(enabled)
        self.queue_list.setEnabled(enabled)
        self._update_actions()

    def add_or_update_job(self, state: TranscriptJobState) -> None:
        self._jobs[state.job_id] = state
        existing = self._find_item(state.job_id)
        label = self._label_for_state(state)
        if existing is None:
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, state.job_id)
            self.queue_list.addItem(item)
        else:
            existing.setText(label)
        self.progress_bar.setValue(state.progress_percent)
        self.status_label.setText(f"Transcript Status: {state.status.value.title()} · {state.progress_percent}%")
        self._update_actions()

    def selected_job(self) -> TranscriptJobState | None:
        item = self.queue_list.currentItem()
        if item is None:
            return None
        job_id = str(item.data(Qt.ItemDataRole.UserRole))
        return self._jobs.get(job_id)

    def _emit_cancel(self) -> None:
        state = self.selected_job()
        if state is not None:
            self.cancel_requested.emit(state.job_id)

    def _emit_retry(self) -> None:
        state = self.selected_job()
        if state is not None:
            self.retry_requested.emit(state.video_id, state.model_name)

    def _update_actions(self) -> None:
        state = self.selected_job()
        can_cancel = state is not None and state.status in {TranscriptStatus.QUEUED, TranscriptStatus.RUNNING}
        can_retry = state is not None and state.status in {
            TranscriptStatus.FAILED,
            TranscriptStatus.CANCELLED,
            TranscriptStatus.COMPLETED,
        }
        self.cancel_button.setEnabled(can_cancel)
        self.retry_button.setEnabled(can_retry)

    def _find_item(self, job_id: str) -> QListWidgetItem | None:
        for index in range(self.queue_list.count()):
            item = self.queue_list.item(index)
            if str(item.data(Qt.ItemDataRole.UserRole)) == job_id:
                return item
        return None

    def _label_for_state(self, state: TranscriptJobState) -> str:
        detail = state.error_message if state.error_message else state.model_name
        return f"{state.video_id[:8]} · {state.status.value} · {state.progress_percent}% · {detail}"
