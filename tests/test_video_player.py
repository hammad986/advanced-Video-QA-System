from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from PySide6.QtGui import QColor, QImage
from PySide6.QtMultimediaWidgets import QVideoWidget

from desktop_app.player.frame_provider import FrameProvider, SnapshotError
from desktop_app.player.playback_controller import PlaybackController
from desktop_app.player.timeline_controller import TimelineController, format_time
from desktop_app.player.video_player import VideoPlayer


def test_timeline_controller_formats_and_clamps_time() -> None:
    timeline = TimelineController()

    timeline.set_duration(125_000)
    timeline.set_position(130_000)

    assert timeline.state.position_ms == 125_000
    assert timeline.state.position_label == "02:05"
    assert format_time(3_661_000) == "1:01:01"
    assert timeline.seek_ratio(0.5) == 62_500


def test_frame_provider_exports_png(tmp_path) -> None:
    image = QImage(64, 48, QImage.Format.Format_RGB32)
    image.fill(QColor("red"))
    output_path = tmp_path / "Snapshots" / "frame.png"

    saved = FrameProvider().save_image(image, output_path)

    assert saved == output_path
    assert output_path.exists()
    assert output_path.suffix == ".png"


def test_frame_provider_rejects_empty_image(tmp_path) -> None:
    with pytest.raises(SnapshotError):
        FrameProvider().save_image(QImage(), tmp_path / "empty.png")


def test_playback_controller_volume_mute_speed_and_frame_steps(qapp) -> None:
    video_widget = QVideoWidget()
    controller = PlaybackController(video_widget)
    observed_positions: list[int] = []
    controller.player.setPosition(1_000)
    controller.seek = observed_positions.append  # type: ignore[method-assign]

    controller.set_volume(35)
    controller.set_muted(True)
    controller.set_speed(1.5)
    controller.step_forward()
    controller.step_backward()

    assert round(controller.audio_output.volume(), 2) == 0.35
    assert controller.audio_output.isMuted() is True
    assert controller.player.playbackRate() == 1.5
    assert observed_positions == [controller.player.position() + controller.FRAME_STEP_MS, 0]


def test_video_player_opens_supported_video_sources(qapp, tmp_path) -> None:
    video_player = VideoPlayer()
    for extension in (".mp4", ".mkv", ".webm", ".avi"):
        source = tmp_path / f"sample{extension}"
        source.write_bytes(b"placeholder")

        video_player.open_video(source, project_workspace=tmp_path)

        assert video_player.current_video_path == source
        assert video_player.title_label.text() == source.name
        assert video_player.play_button.isEnabled() is True


def test_video_player_snapshot_export_uses_project_workspace(qapp, tmp_path) -> None:
    video_player = VideoPlayer()
    source = tmp_path / "sample.mp4"
    source.write_bytes(b"placeholder")
    image = QImage(32, 32, QImage.Format.Format_RGB32)
    image.fill(QColor("blue"))

    class FakeFrameProvider(FrameProvider):
        def export_png(self, output_path: Path) -> Path:
            return self.save_image(image, output_path)

    video_player.frame_provider = FakeFrameProvider()
    video_player.open_video(source, project_workspace=tmp_path)

    snapshot = video_player.export_snapshot()

    assert snapshot.exists()
    assert snapshot.parent == tmp_path / "Snapshots"
    assert snapshot.suffix == ".png"


def test_ffmpeg_generated_small_large_and_supported_formats_open(qapp, tmp_path) -> None:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is required for generated playback validation videos.")
    sources = {
        "mp4": tmp_path / "small.mp4",
        "mkv": tmp_path / "small.mkv",
        "webm": tmp_path / "small.webm",
        "avi": tmp_path / "small.avi",
        "large": tmp_path / "large.webm",
    }
    commands = [
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=15", "-t", "1", str(sources["mp4"])],
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=15", "-t", "1", str(sources["mkv"])],
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=15", "-t", "1", str(sources["webm"])],
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=160x90:rate=15", "-t", "1", "-c:v", "mpeg4", str(sources["avi"])],
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=size=640x360:rate=30", "-t", "2", str(sources["large"])],
    ]
    for command in commands:
        subprocess.run(command, check=True, capture_output=True, text=True)

    video_player = VideoPlayer()
    for source in sources.values():
        video_player.open_video(source, project_workspace=tmp_path)
        assert video_player.current_video_path == source
        video_player.playback.pause()
        video_player.playback.seek(250)
        video_player.playback.set_speed(2.0)
        assert video_player.playback.player.playbackRate() == 2.0
