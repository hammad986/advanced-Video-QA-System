from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path


class VideoMetadataError(RuntimeError):
    pass


@dataclass(frozen=True)
class VideoMetadata:
    duration: float
    fps: float
    width: int
    height: int


class VideoMetadataExtractor:
    def extract(self, video_path: Path) -> VideoMetadata:
        if shutil.which("ffprobe") is None:
            raise VideoMetadataError("ffprobe is required for video metadata extraction.")
        command = [
            "ffprobe",
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height,avg_frame_rate,r_frame_rate",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(video_path),
        ]
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise VideoMetadataError("Could not read video metadata.") from exc

        try:
            payload = json.loads(result.stdout)
            stream = payload.get("streams", [{}])[0]
            duration = float(payload.get("format", {}).get("duration") or 0.0)
            fps = self._parse_fps(stream.get("avg_frame_rate") or stream.get("r_frame_rate") or "0/1")
            width = int(stream.get("width") or 0)
            height = int(stream.get("height") or 0)
        except (ValueError, TypeError, IndexError, KeyError) as exc:
            raise VideoMetadataError("Video metadata response is invalid.") from exc

        if duration <= 0 or width <= 0 or height <= 0:
            raise VideoMetadataError("Video metadata is incomplete.")
        return VideoMetadata(duration=duration, fps=fps, width=width, height=height)

    def _parse_fps(self, value: str) -> float:
        try:
            fraction = Fraction(value)
        except (ValueError, ZeroDivisionError):
            return 0.0
        if fraction.denominator == 0:
            return 0.0
        return float(fraction)

