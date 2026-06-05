from __future__ import annotations

import gc
import contextlib
import hashlib
import os
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Callable, Protocol

from desktop_app.core.frozen_runtime import configure_frozen_runtime_paths
from desktop_app.transcripts.transcript_models import (
    TranscriptModelName,
    TranscriptionResult,
    TranscriptionSegmentResult,
)


ProgressCallback = Callable[[int, str], None]


class TranscriptionError(RuntimeError):
    pass


class TranscriptionCancelled(TranscriptionError):
    pass


class TranscriptionEngineUnavailable(TranscriptionError):
    pass


class CancellationToken:
    def __init__(self) -> None:
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        self._cancelled.set()

    @property
    def is_cancelled(self) -> bool:
        return self._cancelled.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise TranscriptionCancelled("Transcription was cancelled.")


class TranscriptionEngine(Protocol):
    def transcribe(self, audio_path: Path, token: CancellationToken) -> TranscriptionResult:
        ...

    def unload(self) -> None:
        ...


class WhisperTranscriptionEngine:
    def __init__(self, model_name: str, *, device: str = "cpu", compute_type: str = "int8") -> None:
        if model_name not in {item.value for item in TranscriptModelName}:
            raise TranscriptionError(f"Unsupported transcript model: {model_name}")
        self.model_name = model_name
        self.device = device
        self.compute_type = compute_type
        self._engine_kind = ""
        self._model = self._load_model()

    def _load_model(self) -> object:
        configure_frozen_runtime_paths()
        faster_whisper_error = ""
        try:
            from faster_whisper import WhisperModel

            self._engine_kind = "faster-whisper"
            return WhisperModel(self.model_name, device=self.device, compute_type=self.compute_type)
        except ImportError as exc:
            faster_whisper_error = f"{exc.__class__.__name__}: {exc}"
            try:
                import whisper

                self._engine_kind = "whisper"
                return _load_openai_whisper_model_with_cache_recovery(whisper, self.model_name, self.device)
            except ImportError as exc:
                raise TranscriptionEngineUnavailable(
                    "Install faster-whisper or openai-whisper to generate transcripts. "
                    f"faster-whisper import failed with {faster_whisper_error}; "
                    f"openai-whisper import failed with {exc.__class__.__name__}: {exc}."
                ) from exc

    def transcribe(self, audio_path: Path, token: CancellationToken) -> TranscriptionResult:
        token.raise_if_cancelled()
        if self._engine_kind == "faster-whisper":
            return self._transcribe_faster_whisper(audio_path, token)
        return self._transcribe_openai_whisper(audio_path, token)

    def unload(self) -> None:
        self._model = None
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def _transcribe_faster_whisper(self, audio_path: Path, token: CancellationToken) -> TranscriptionResult:
        segments_iter, info = self._model.transcribe(str(audio_path), vad_filter=True)  # type: ignore[attr-defined]
        segments: list[TranscriptionSegmentResult] = []
        for segment in segments_iter:
            token.raise_if_cancelled()
            text = str(getattr(segment, "text", "")).strip()
            if not text:
                continue
            confidence = float(getattr(segment, "avg_logprob", 0.0) or 0.0)
            segments.append(
                TranscriptionSegmentResult(
                    start_time=float(getattr(segment, "start", 0.0) or 0.0),
                    end_time=float(getattr(segment, "end", 0.0) or 0.0),
                    text=text,
                    confidence=confidence,
                )
            )
        return TranscriptionResult(language=str(getattr(info, "language", "") or ""), segments=segments)

    def _transcribe_openai_whisper(self, audio_path: Path, token: CancellationToken) -> TranscriptionResult:
        output = self._model.transcribe(str(audio_path))  # type: ignore[attr-defined]
        token.raise_if_cancelled()
        segments = [
            TranscriptionSegmentResult(
                start_time=float(segment.get("start", 0.0) or 0.0),
                end_time=float(segment.get("end", 0.0) or 0.0),
                text=str(segment.get("text", "")).strip(),
                confidence=float(segment.get("avg_logprob", 0.0) or 0.0),
            )
            for segment in output.get("segments", [])
            if str(segment.get("text", "")).strip()
        ]
        return TranscriptionResult(language=str(output.get("language", "") or ""), segments=segments)


class TranscriptionWorker:
    def __init__(
        self,
        *,
        model_name: str,
        engine_factory: Callable[[str], TranscriptionEngine] | None = None,
    ) -> None:
        self.model_name = model_name
        self.engine_factory = engine_factory or (lambda model: WhisperTranscriptionEngine(model))

    def run(
        self,
        video_path: Path,
        token: CancellationToken,
        progress: ProgressCallback | None = None,
    ) -> TranscriptionResult:
        self._emit(progress, 5, "Preparing audio extraction")
        token.raise_if_cancelled()
        with tempfile.TemporaryDirectory(prefix="avqa_transcript_") as temp_dir:
            audio_path = Path(temp_dir) / f"{video_path.stem}.wav"
            self.extract_audio(video_path, audio_path, token)
            self._emit(progress, 35, "Audio extracted")
            token.raise_if_cancelled()
            engine = self.engine_factory(self.model_name)
            try:
                self._emit(progress, 45, f"Transcribing with {self.model_name}")
                result = engine.transcribe(audio_path, token)
                token.raise_if_cancelled()
                self._emit(progress, 95, "Persisting transcript")
                return result
            finally:
                self._unload_engine(engine)

    def extract_audio(self, video_path: Path, audio_path: Path, token: CancellationToken) -> Path:
        if shutil.which("ffmpeg") is None:
            raise TranscriptionError("ffmpeg is required for audio extraction.")
        command = [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-acodec",
            "pcm_s16le",
            str(audio_path),
        ]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        while process.poll() is None:
            if token.is_cancelled:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                raise TranscriptionCancelled("Transcription was cancelled during audio extraction.")
            time.sleep(0.05)
        _, stderr = process.communicate()
        if process.returncode != 0:
            raise TranscriptionError(f"Audio extraction failed: {stderr.strip()}")
        if not audio_path.exists():
            raise TranscriptionError("Audio extraction did not create an output file.")
        return audio_path

    def _emit(self, callback: ProgressCallback | None, percent: int, message: str) -> None:
        if callback:
            callback(percent, message)

    def _unload_engine(self, engine: TranscriptionEngine) -> None:
        try:
            engine.unload()
        except Exception:
            pass
        gc.collect()


def _load_openai_whisper_model_with_cache_recovery(whisper_module: object, model_name: str, device: str) -> object:
    cache_path, expected_sha256 = _openai_whisper_cache_target(whisper_module, model_name)
    lock_path = cache_path.with_suffix(cache_path.suffix + ".lock") if cache_path is not None else None
    with _openai_whisper_cache_lock(lock_path):
        try:
            return whisper_module.load_model(model_name, device=device)  # type: ignore[attr-defined]
        except RuntimeError as exc:
            if not _is_openai_whisper_checksum_error(exc):
                raise
            actual_sha256 = _sha256_file(cache_path)
            if cache_path is not None and cache_path.exists():
                cache_path.unlink()
            try:
                return whisper_module.load_model(model_name, device=device)  # type: ignore[attr-defined]
            except RuntimeError as retry_exc:
                if _is_openai_whisper_checksum_error(retry_exc):
                    retry_actual_sha256 = _sha256_file(cache_path)
                    raise TranscriptionError(
                        "OpenAI Whisper model cache failed SHA256 validation after one automatic retry. "
                        f"model={model_name}; cache_path={cache_path}; expected_sha256={expected_sha256}; "
                        f"actual_sha256={retry_actual_sha256 or actual_sha256 or 'unavailable'}."
                    ) from retry_exc
                raise


def _openai_whisper_cache_target(whisper_module: object, model_name: str) -> tuple[Path | None, str]:
    models = getattr(whisper_module, "_MODELS", {})
    url = models.get(model_name) if isinstance(models, dict) else None
    if not isinstance(url, str):
        return None, ""
    expected_sha256 = url.split("/")[-2]
    default_root = Path(os.path.expanduser("~")) / ".cache"
    cache_root = Path(os.getenv("XDG_CACHE_HOME", str(default_root))) / "whisper"
    return cache_root / url.rsplit("/", 1)[-1], expected_sha256


def _is_openai_whisper_checksum_error(exc: RuntimeError) -> bool:
    return "SHA256 checksum does not not match" in str(exc)


def _sha256_file(path: Path | None) -> str:
    if path is None or not path.is_file():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@contextlib.contextmanager
def _openai_whisper_cache_lock(lock_path: Path | None):
    if lock_path is None:
        yield
        return
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as lock_file:
        lock_file.seek(0)
        if lock_file.read(1) == b"":
            lock_file.write(b"0")
            lock_file.flush()
        lock_file.seek(0)
        _lock_file(lock_file)
        try:
            yield
        finally:
            _unlock_file(lock_file)


def _lock_file(lock_file: object) -> None:
    if os.name == "nt":
        import msvcrt

        msvcrt.locking(lock_file.fileno(), msvcrt.LK_LOCK, 1)  # type: ignore[attr-defined]
        return
    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)  # type: ignore[attr-defined]


def _unlock_file(lock_file: object) -> None:
    if os.name == "nt":
        import msvcrt

        lock_file.seek(0)  # type: ignore[attr-defined]
        msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)  # type: ignore[attr-defined]
        return
    import fcntl

    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)  # type: ignore[attr-defined]
