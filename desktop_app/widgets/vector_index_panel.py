from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QGroupBox, QLabel, QPushButton, QProgressBar, QVBoxLayout, QWidget

from desktop_app.vector_store.vector_manager import VectorIndexJobState, VectorIndexStatus


class VectorIndexPanelWidget(QGroupBox):
    build_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Vector Store", parent)
        self.status_label = QLabel("No FAISS index built")
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.build_button = QPushButton("Build FAISS Index")

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.build_button)

        self.build_button.clicked.connect(self.build_requested)

    def reset_for_project(self, index_path: str = "") -> None:
        self.progress_bar.setValue(0)
        self.build_button.setEnabled(True)
        self.status_label.setText(f"Latest index: {index_path}" if index_path else "No FAISS index built")

    def apply_state(self, state: VectorIndexJobState) -> None:
        self.progress_bar.setValue(state.progress_percent)
        self.build_button.setEnabled(state.status not in {VectorIndexStatus.QUEUED, VectorIndexStatus.RUNNING})
        if state.status == VectorIndexStatus.COMPLETED:
            self.status_label.setText(f"FAISS index built: {state.vector_count} vectors")
        elif state.status == VectorIndexStatus.FAILED:
            self.status_label.setText(f"FAISS index failed: {state.error_message}")
        else:
            self.status_label.setText(f"FAISS index {state.status.value}: {state.progress_percent}%")
