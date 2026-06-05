from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop_app.compare.compare_models import CompareJobState, CompareResult, CompareStatus
from desktop_app.videos.video_model import VideoRecord
from desktop_app.widgets.compare_result_view import CompareResultView


class CompareWorkspaceWidget(QGroupBox):
    compare_requested = Signal(str, list, str, float)
    evidence_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Multi-Video Compare", parent)
        self.status_label = QLabel("Select 2-10 videos and enter a comparison question.")
        self.session_name_input = QLineEdit()
        self.session_name_input.setPlaceholderText("Session name")
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Compare machine learning definitions")
        self.video_list = QListWidget()
        self.video_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        self.video_list.setMaximumHeight(120)
        self.threshold_input = QDoubleSpinBox()
        self.threshold_input.setRange(0.0, 1.0)
        self.threshold_input.setSingleStep(0.05)
        self.threshold_input.setValue(0.0)
        self.compare_button = QPushButton("Compare Videos")
        self.result_view = CompareResultView()

        control_row = QHBoxLayout()
        control_row.addWidget(QLabel("Min"))
        control_row.addWidget(self.threshold_input)
        control_row.addWidget(self.compare_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.session_name_input)
        layout.addWidget(self.query_input)
        layout.addWidget(QLabel("Videos"))
        layout.addWidget(self.video_list)
        layout.addLayout(control_row)
        layout.addWidget(self.result_view, 1)

        self.compare_button.clicked.connect(self._emit_compare_requested)
        self.result_view.evidence_selected.connect(self.evidence_selected)

    def set_videos(self, videos: list[VideoRecord]) -> None:
        selected = set(self.selected_video_ids())
        self.video_list.clear()
        for video in videos:
            item = QListWidgetItem(video.name)
            item.setData(Qt.ItemDataRole.UserRole, video.id)
            item.setSelected(video.id in selected)
            self.video_list.addItem(item)
        self.status_label.setText(f"{len(videos):,} videos available for comparison")

    def selected_video_ids(self) -> list[str]:
        video_ids: list[str] = []
        for item in self.video_list.selectedItems():
            value = item.data(Qt.ItemDataRole.UserRole)
            if value:
                video_ids.append(str(value))
        return video_ids

    def set_result(self, result: CompareResult) -> None:
        self.result_view.set_result(result)
        self.status_label.setText(
            f"Compared {len(result.video_ids)} videos · {len(result.evidence_items)} evidence items"
        )
        self.compare_button.setEnabled(True)

    def apply_state(self, state: CompareJobState) -> None:
        running = state.status in {CompareStatus.QUEUED, CompareStatus.RUNNING}
        self.compare_button.setEnabled(not running)
        if state.status == CompareStatus.FAILED:
            self.status_label.setText(f"Compare failed: {state.error_message}")
        elif state.status == CompareStatus.COMPLETED:
            self.status_label.setText(f"Compare ready · {state.finding_count} findings")
        else:
            self.status_label.setText(f"Compare {state.status.value}: {state.progress_percent}%")

    def _emit_compare_requested(self) -> None:
        video_ids = self.selected_video_ids()
        query = self.query_input.text().strip()
        if not query:
            return
        self.compare_requested.emit(
            self.session_name_input.text().strip() or "Multi-Video Compare",
            video_ids,
            query,
            float(self.threshold_input.value()),
        )
