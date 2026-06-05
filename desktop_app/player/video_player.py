from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtMultimedia import QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from desktop_app.player.frame_provider import FrameProvider, SnapshotError
from desktop_app.player.playback_controller import PlaybackController
from desktop_app.player.timeline_controller import TimelineController


class VideoPlayer(QWidget):
    snapshot_requested = Signal()
    error_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.region_name = "center"
        self.current_video_path: Path | None = None
        self.current_project_workspace: Path | None = None
        self._updating_timeline = False

        self.video_widget = QVideoWidget()
        self.video_widget.setMinimumHeight(320)
        self.playback = PlaybackController(self.video_widget)
        self.timeline = TimelineController()
        self.frame_provider = FrameProvider(self.video_widget.videoSink())

        self.title_label = QLabel("Video Workspace")
        self.title_label.setObjectName("RegionTitle")
        self.time_label = QLabel("00:00 / 00:00")

        self.play_button = QPushButton("Play")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.step_back_button = QPushButton("Frame -")
        self.step_forward_button = QPushButton("Frame +")
        self.snapshot_button = QPushButton("Snapshot")

        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(0, 0)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(75)
        self.volume_slider.setMaximumWidth(140)
        self.mute_checkbox = QCheckBox("Mute")

        self.speed_combo = QComboBox()
        for speed in (0.5, 1.0, 1.25, 1.5, 2.0):
            self.speed_combo.addItem(f"{speed:g}x", speed)
        self.speed_combo.setCurrentIndex(1)

        controls = QHBoxLayout()
        for widget in (
            self.play_button,
            self.pause_button,
            self.stop_button,
            self.step_back_button,
            self.step_forward_button,
            self.snapshot_button,
        ):
            controls.addWidget(widget)
        controls.addStretch(1)
        controls.addWidget(QLabel("Speed"))
        controls.addWidget(self.speed_combo)
        controls.addWidget(QLabel("Volume"))
        controls.addWidget(self.volume_slider)
        controls.addWidget(self.mute_checkbox)

        timeline_row = QHBoxLayout()
        timeline_row.addWidget(self.timeline_slider, 1)
        timeline_row.addWidget(self.time_label)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        layout.addWidget(self.title_label)
        layout.addWidget(self.video_widget, 1)
        layout.addLayout(timeline_row)
        layout.addLayout(controls)

        self.play_button.clicked.connect(self.playback.play)
        self.pause_button.clicked.connect(self.playback.pause)
        self.stop_button.clicked.connect(self.playback.stop)
        self.step_back_button.clicked.connect(self.playback.step_backward)
        self.step_forward_button.clicked.connect(self.playback.step_forward)
        self.snapshot_button.clicked.connect(self.snapshot_requested.emit)
        self.timeline_slider.sliderMoved.connect(self.playback.seek)
        self.volume_slider.valueChanged.connect(self.playback.set_volume)
        self.mute_checkbox.toggled.connect(self.playback.set_muted)
        self.speed_combo.currentIndexChanged.connect(self._apply_speed)
        self.playback.player.positionChanged.connect(self._handle_position_changed)
        self.playback.player.durationChanged.connect(self._handle_duration_changed)
        self.playback.player.errorOccurred.connect(self._handle_error)
        self._set_controls_enabled(False)

    def open_video(self, file_path: str | Path, *, project_workspace: str | Path | None = None) -> None:
        self.current_video_path = Path(file_path)
        self.current_project_workspace = Path(project_workspace) if project_workspace else None
        self.title_label.setText(self.current_video_path.name)
        self.playback.open_video(self.current_video_path)
        self._set_controls_enabled(True)

    def export_snapshot(self) -> Path:
        if self.current_project_workspace is None:
            raise SnapshotError("Open a project before exporting snapshots.")
        if self.current_video_path is None:
            raise SnapshotError("Open a video before exporting snapshots.")
        snapshots_dir = self.current_project_workspace / "Snapshots"
        timestamp = int(time.time() * 1000)
        output_path = snapshots_dir / f"{self.current_video_path.stem}_{timestamp}.png"
        return self.frame_provider.export_png(output_path)

    def _set_controls_enabled(self, enabled: bool) -> None:
        for widget in (
            self.play_button,
            self.pause_button,
            self.stop_button,
            self.step_back_button,
            self.step_forward_button,
            self.snapshot_button,
            self.timeline_slider,
            self.volume_slider,
            self.mute_checkbox,
            self.speed_combo,
        ):
            widget.setEnabled(enabled)

    def _handle_position_changed(self, position_ms: int) -> None:
        state = self.timeline.set_position(position_ms)
        self._updating_timeline = True
        self.timeline_slider.setValue(state.position_ms)
        self._updating_timeline = False
        self._update_time_label()

    def _handle_duration_changed(self, duration_ms: int) -> None:
        state = self.timeline.set_duration(duration_ms)
        self.timeline_slider.setRange(0, state.duration_ms)
        self._update_time_label()

    def _update_time_label(self) -> None:
        self.time_label.setText(f"{self.timeline.state.position_label} / {self.timeline.state.duration_label}")

    def _apply_speed(self) -> None:
        self.playback.set_speed(float(self.speed_combo.currentData()))

    def _handle_error(self, error: QMediaPlayer.Error, error_text: str) -> None:
        if error == QMediaPlayer.Error.NoError:
            return
        self.error_changed.emit(error_text or "Video playback error.")
