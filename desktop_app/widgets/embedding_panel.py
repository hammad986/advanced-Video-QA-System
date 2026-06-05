from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from desktop_app.embeddings.embedding_models import (
    DEFAULT_EMBEDDING_MODELS,
    OPTIONAL_EMBEDDING_MODELS,
    EmbeddingJobState,
    EmbeddingStatus,
)


class EmbeddingPanelWidget(QGroupBox):
    generate_requested = Signal(str)
    cancel_requested = Signal(str)
    retry_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Embeddings", parent)
        self._current_job_id: str | None = None
        self._last_model_name: str | None = None

        self.status_label = QLabel("No embeddings generated")
        self.model_combo = QComboBox()
        for model_name in DEFAULT_EMBEDDING_MODELS:
            self.model_combo.addItem(model_name, model_name)
        for model_name in OPTIONAL_EMBEDDING_MODELS:
            self.model_combo.addItem(f"{model_name} (optional)", model_name)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.generate_button = QPushButton("Generate Embeddings")
        self.cancel_button = QPushButton("Cancel")
        self.retry_button = QPushButton("Retry")
        self.cancel_button.setEnabled(False)
        self.retry_button.setEnabled(False)

        button_layout = QHBoxLayout()
        button_layout.addWidget(self.generate_button)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.retry_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.model_combo)
        layout.addWidget(self.progress_bar)
        layout.addLayout(button_layout)

        self.generate_button.clicked.connect(self._emit_generate)
        self.cancel_button.clicked.connect(self._emit_cancel)
        self.retry_button.clicked.connect(self._emit_retry)

    def selected_model(self) -> str:
        return str(self.model_combo.currentData())

    def reset_for_transcript(self, embedded_count: int = 0) -> None:
        self._current_job_id = None
        self.progress_bar.setValue(0)
        if embedded_count:
            self.status_label.setText(f"Embeddings ready: {embedded_count}")
        else:
            self.status_label.setText("No embeddings generated")
        self.generate_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.retry_button.setEnabled(False)

    def apply_state(self, state: EmbeddingJobState) -> None:
        self._current_job_id = state.job_id
        self._last_model_name = state.model_name
        self.progress_bar.setValue(state.progress_percent)
        self.status_label.setText(self._format_status(state))
        running = state.status in {EmbeddingStatus.QUEUED, EmbeddingStatus.RUNNING}
        self.generate_button.setEnabled(not running)
        self.cancel_button.setEnabled(running)
        self.retry_button.setEnabled(state.status in {EmbeddingStatus.FAILED, EmbeddingStatus.CANCELLED})

    def _format_status(self, state: EmbeddingJobState) -> str:
        if state.status == EmbeddingStatus.COMPLETED:
            return f"Embeddings complete: {state.record_count} chunks"
        if state.status == EmbeddingStatus.FAILED:
            return f"Embeddings failed: {state.error_message}"
        if state.status == EmbeddingStatus.CANCELLED:
            return "Embedding generation cancelled"
        return f"Embeddings {state.status.value}: {state.progress_percent}%"

    def _emit_generate(self) -> None:
        self._last_model_name = self.selected_model()
        self.generate_requested.emit(self._last_model_name)

    def _emit_cancel(self) -> None:
        if self._current_job_id:
            self.cancel_requested.emit(self._current_job_id)

    def _emit_retry(self) -> None:
        if self._last_model_name:
            self.retry_requested.emit(self._last_model_name)
