from __future__ import annotations

import multiprocessing as mp
import queue
import time
import traceback
from pathlib import Path
from typing import Any, Callable

from desktop_app.core.frozen_runtime import configure_frozen_runtime_paths
from desktop_app.transcripts.transcript_models import TranscriptionResult
from desktop_app.transcripts.transcription_worker import (
    ProgressCallback,
    TranscriptionCancelled,
    TranscriptionError,
    TranscriptionWorker,
)


class ProcessTranscriptionError(TranscriptionError):
    pass


class _ProcessCancellationToken:
    def __init__(self, cancel_event: Any) -> None:
        self.cancel_event = cancel_event

    def cancel(self) -> None:
        self.cancel_event.set()

    @property
    def is_cancelled(self) -> bool:
        return bool(self.cancel_event.is_set())

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled:
            raise TranscriptionCancelled("Transcription was cancelled.")


def _transcription_child_entry(payload: dict[str, Any], event_queue: Any, cancel_event: Any) -> None:
    try:
        configure_frozen_runtime_paths()
        token = _ProcessCancellationToken(cancel_event)
        worker = TranscriptionWorker(model_name=str(payload["model_name"]))

        def progress(percent: int, message: str) -> None:
            event_queue.put({"type": "progress", "percent": percent, "message": message})

        result = worker.run(Path(str(payload["video_path"])), token, progress)
        event_queue.put({"type": "result", "result": result})
    except BaseException as exc:
        event_queue.put(
            {
                "type": "error",
                "error": str(exc),
                "class": exc.__class__.__name__,
                "traceback": traceback.format_exc(),
            }
        )


class ProcessTranscriptionWorker:
    def __init__(
        self,
        *,
        model_name: str,
        process_target: Callable[[dict[str, Any], Any, Any], None] | None = None,
        max_restarts: int = 1,
    ) -> None:
        self.model_name = model_name
        self.process_target = process_target or _transcription_child_entry
        self.max_restarts = max(0, max_restarts)

    def run(
        self,
        video_path: Path,
        token: Any,
        progress: ProgressCallback | None = None,
    ) -> TranscriptionResult:
        payload = {"video_path": str(video_path), "model_name": self.model_name}
        attempts = self.max_restarts + 1
        last_error = ""
        for attempt in range(1, attempts + 1):
            result, last_error = self._run_once(payload, token, progress)
            if result is not None:
                return result
            if _token_cancelled(token):
                raise TranscriptionCancelled("Transcription was cancelled.")
            if attempt < attempts:
                time.sleep(0.2)
        raise ProcessTranscriptionError(last_error or "Transcription process failed.")

    def _run_once(
        self,
        payload: dict[str, Any],
        token: Any,
        progress: ProgressCallback | None,
    ) -> tuple[TranscriptionResult | None, str]:
        context = mp.get_context("spawn")
        event_queue = context.Queue()
        cancel_event = context.Event()
        process = context.Process(target=self.process_target, args=(payload, event_queue, cancel_event), daemon=True)
        process.start()
        last_error = ""
        try:
            while process.is_alive() or not event_queue.empty():
                if _token_cancelled(token):
                    cancel_event.set()
                try:
                    event = event_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                event_type = event.get("type")
                if event_type == "progress" and progress is not None:
                    progress(int(event.get("percent", 0)), str(event.get("message", "")))
                elif event_type == "result":
                    process.join(timeout=5)
                    return event["result"], ""
                elif event_type == "error":
                    last_error = f"{event.get('class', 'ProcessError')}: {event.get('error', '')}"
                    process.join(timeout=5)
                    if event.get("class") == "TranscriptionCancelled":
                        raise TranscriptionCancelled("Transcription was cancelled.")
                    return None, last_error
            process.join(timeout=5)
            if process.exitcode not in (0, None):
                return None, f"Transcription process exited with code {process.exitcode}."
            return None, last_error or "Transcription process exited without a result."
        finally:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
            try:
                event_queue.close()
                event_queue.join_thread()
            except Exception:
                pass


def _token_cancelled(token: Any) -> bool:
    value = getattr(token, "is_cancelled", False)
    if callable(value):
        return bool(value())
    return bool(value)
