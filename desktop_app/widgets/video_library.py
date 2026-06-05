from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop_app.videos.video_model import VideoRecord


class VideoLibraryWidget(QWidget):
    import_requested = Signal()
    open_requested = Signal(str)
    remove_requested = Signal(str)
    refresh_requested = Signal()
    search_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.region_name = "video-library"
        self._videos: list[VideoRecord] = []

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search videos")
        self.search_input.textChanged.connect(self.search_changed.emit)

        self.view_mode = QComboBox()
        self.view_mode.addItem("Thumbnail View", "thumbnail")
        self.view_mode.addItem("List View", "list")
        self.view_mode.currentIndexChanged.connect(self.apply_view_mode)

        self.import_button = QPushButton("Import Video")
        self.open_button = QPushButton("Open Video")
        self.remove_button = QPushButton("Remove Video")
        self.refresh_button = QPushButton("Refresh Library")
        self.import_button.clicked.connect(self.import_requested.emit)
        self.open_button.clicked.connect(self._emit_open_requested)
        self.remove_button.clicked.connect(self._emit_remove_requested)
        self.refresh_button.clicked.connect(self.refresh_requested.emit)

        self.video_list = QListWidget()
        self.video_list.setIconSize(QSize(160, 90))
        self.video_list.currentRowChanged.connect(lambda _: self._update_actions())
        self.video_list.itemDoubleClicked.connect(lambda _: self._emit_open_requested())

        control_row = QHBoxLayout()
        control_row.addWidget(self.import_button)
        control_row.addWidget(self.open_button)
        control_row.addWidget(self.remove_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(6)
        layout.addWidget(self.search_input)
        layout.addWidget(self.view_mode)
        layout.addLayout(control_row)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.video_list, 1)

        self.apply_view_mode()
        self._update_actions()

    def set_videos(self, videos: list[VideoRecord]) -> None:
        self._videos = videos
        self.video_list.clear()
        for video in videos:
            item = QListWidgetItem(self._label_for_video(video))
            item.setData(Qt.ItemDataRole.UserRole, video.id)
            thumbnail_path = Path(video.thumbnail_path)
            if thumbnail_path.exists():
                item.setIcon(QIcon(str(thumbnail_path)))
            self.video_list.addItem(item)
        self._update_actions()

    def selected_video_id(self) -> str | None:
        item = self.video_list.currentItem()
        if item is None:
            return None
        value = item.data(Qt.ItemDataRole.UserRole)
        return str(value) if value else None

    def set_library_enabled(self, enabled: bool) -> None:
        self.import_button.setEnabled(enabled)
        self.open_button.setEnabled(enabled)
        self.refresh_button.setEnabled(enabled)
        self.search_input.setEnabled(enabled)
        self.view_mode.setEnabled(enabled)
        self.video_list.setEnabled(enabled)
        self._update_actions()

    def apply_view_mode(self) -> None:
        mode = str(self.view_mode.currentData())
        if mode == "thumbnail":
            self.video_list.setViewMode(QListWidget.ViewMode.IconMode)
            self.video_list.setResizeMode(QListWidget.ResizeMode.Adjust)
            self.video_list.setMovement(QListWidget.Movement.Static)
            self.video_list.setGridSize(QSize(190, 145))
        else:
            self.video_list.setViewMode(QListWidget.ViewMode.ListMode)
            self.video_list.setGridSize(QSize())

    def _emit_remove_requested(self) -> None:
        video_id = self.selected_video_id()
        if video_id:
            self.remove_requested.emit(video_id)

    def _emit_open_requested(self) -> None:
        video_id = self.selected_video_id()
        if video_id:
            self.open_requested.emit(video_id)

    def _update_actions(self) -> None:
        self.open_button.setEnabled(self.isEnabled() and self.selected_video_id() is not None)
        self.remove_button.setEnabled(self.isEnabled() and self.selected_video_id() is not None)

    def _label_for_video(self, video: VideoRecord) -> str:
        duration = self._format_duration(video.duration)
        size_mb = video.file_size / (1024 * 1024)
        return f"{video.name}\n{video.width}x{video.height} · {video.fps:.2f} fps · {duration} · {size_mb:.1f} MB"

    def _format_duration(self, duration: float) -> str:
        total_seconds = int(duration)
        minutes, seconds = divmod(total_seconds, 60)
        hours, minutes = divmod(minutes, 60)
        if hours:
            return f"{hours}:{minutes:02d}:{seconds:02d}"
        return f"{minutes}:{seconds:02d}"
