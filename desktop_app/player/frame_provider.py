from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QImage
from PySide6.QtMultimedia import QVideoFrame, QVideoSink


class SnapshotError(RuntimeError):
    pass


class FrameProvider:
    def __init__(self, video_sink: QVideoSink | None = None) -> None:
        self.video_sink = video_sink

    def current_image(self) -> QImage:
        if self.video_sink is None:
            raise SnapshotError("No video sink is available.")
        frame = self.video_sink.videoFrame()
        return self.image_from_frame(frame)

    def image_from_frame(self, frame: QVideoFrame) -> QImage:
        if not frame.isValid():
            raise SnapshotError("No current video frame is available.")
        image = frame.toImage()
        if image.isNull():
            raise SnapshotError("Current video frame could not be converted to an image.")
        return image

    def export_png(self, output_path: Path) -> Path:
        return self.save_image(self.current_image(), output_path)

    def save_image(self, image: QImage, output_path: Path) -> Path:
        if image.isNull():
            raise SnapshotError("Snapshot image is empty.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if not image.save(str(output_path), "PNG"):
            raise SnapshotError("Snapshot could not be saved.")
        return output_path

