from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtMultimediaWidgets import QVideoWidget


class PlaybackController:
    FRAME_STEP_MS = 33

    def __init__(self, video_widget: QVideoWidget) -> None:
        self.video_widget = video_widget
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(video_widget)
        self.audio_output.setVolume(0.75)

    def open_video(self, file_path: str | Path) -> None:
        self.player.setSource(QUrl.fromLocalFile(str(Path(file_path))))

    def play(self) -> None:
        self.player.play()

    def pause(self) -> None:
        self.player.pause()

    def stop(self) -> None:
        self.player.stop()

    def seek(self, position_ms: int) -> None:
        self.player.setPosition(max(0, position_ms))

    def set_volume(self, percent: int) -> None:
        clamped = max(0, min(percent, 100))
        self.audio_output.setVolume(clamped / 100.0)

    def set_muted(self, muted: bool) -> None:
        self.audio_output.setMuted(muted)

    def set_speed(self, speed: float) -> None:
        self.player.setPlaybackRate(speed)

    def step_forward(self) -> None:
        self.seek(self.player.position() + self.FRAME_STEP_MS)

    def step_backward(self) -> None:
        self.seek(max(0, self.player.position() - self.FRAME_STEP_MS))

