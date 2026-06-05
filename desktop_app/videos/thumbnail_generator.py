from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class ThumbnailError(RuntimeError):
    pass


class ThumbnailGenerator:
    def generate(self, video_path: Path, thumbnail_path: Path, *, duration: float) -> Path:
        if shutil.which("ffmpeg") is None:
            raise ThumbnailError("ffmpeg is required for thumbnail generation.")
        thumbnail_path.parent.mkdir(parents=True, exist_ok=True)
        seek_time = max(0.0, min(duration / 2.0, 5.0))
        command = [
            "ffmpeg",
            "-y",
            "-ss",
            f"{seek_time:.3f}",
            "-i",
            str(video_path),
            "-frames:v",
            "1",
            "-vf",
            "scale=320:-1",
            str(thumbnail_path),
        ]
        try:
            subprocess.run(command, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as exc:
            raise ThumbnailError("Could not generate video thumbnail.") from exc
        if not thumbnail_path.exists():
            raise ThumbnailError("Thumbnail was not created.")
        return thumbnail_path

