from __future__ import annotations

import multiprocessing as mp
import queue
import time
import traceback
from typing import Any, Callable

from desktop_app.embeddings.embedding_models import EmbeddingRecord
from desktop_app.embeddings.embedding_worker import (
    CancellationToken,
    EmbeddingCancelled,
    EmbeddingError,
    LocalEmbeddingWorker,
)
from desktop_app.knowledge.knowledge_models import KnowledgeChunk


class ProcessEmbeddingError(EmbeddingError):
    pass


class _ProcessEmbeddingCancellationToken(CancellationToken):
    def __init__(self, cancel_event: Any) -> None:
        self.cancel_event = cancel_event

    def cancel(self) -> None:
        self.cancel_event.set()

    def is_cancelled(self) -> bool:
        return bool(self.cancel_event.is_set())


def _embedding_child_entry(payload: dict[str, Any], event_queue: Any, cancel_event: Any) -> None:
    try:
        token = _ProcessEmbeddingCancellationToken(cancel_event)
        worker = LocalEmbeddingWorker(
            batch_size=int(payload.get("batch_size", 4)),
            auto_unload_after_generate=True,
        )

        def progress(percent: int, message: str) -> None:
            event_queue.put({"type": "progress", "percent": percent, "message": message})

        records = worker.generate(
            list(payload["chunks"]),
            str(payload["model_name"]),
            cancellation_token=token,
            progress_callback=progress,
        )
        event_queue.put({"type": "result", "records": records})
    except BaseException as exc:
        event_queue.put(
            {
                "type": "error",
                "error": str(exc),
                "class": exc.__class__.__name__,
                "traceback": traceback.format_exc(),
            }
        )


class ProcessEmbeddingWorker:
    def __init__(
        self,
        *,
        batch_size: int = 4,
        process_target: Callable[[dict[str, Any], Any, Any], None] | None = None,
        max_restarts: int = 1,
    ) -> None:
        self.batch_size = max(1, batch_size)
        self.process_target = process_target or _embedding_child_entry
        self.max_restarts = max(0, max_restarts)

    def generate(
        self,
        chunks: list[KnowledgeChunk],
        model_name: str,
        cancellation_token: CancellationToken | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> list[EmbeddingRecord]:
        token = cancellation_token or CancellationToken()
        payload = {"chunks": chunks, "model_name": model_name, "batch_size": self.batch_size}
        attempts = self.max_restarts + 1
        last_error = ""
        for attempt in range(1, attempts + 1):
            records, last_error = self._run_once(payload, token, progress_callback)
            if records is not None:
                return records
            if token.is_cancelled():
                raise EmbeddingCancelled("Embedding generation was cancelled.")
            if attempt < attempts:
                time.sleep(0.2)
        raise ProcessEmbeddingError(last_error or "Embedding process failed.")

    def _run_once(
        self,
        payload: dict[str, Any],
        token: CancellationToken,
        progress_callback: Callable[[int, str], None] | None,
    ) -> tuple[list[EmbeddingRecord] | None, str]:
        context = mp.get_context("spawn")
        event_queue = context.Queue()
        cancel_event = context.Event()
        process = context.Process(target=self.process_target, args=(payload, event_queue, cancel_event), daemon=True)
        process.start()
        last_error = ""
        try:
            while process.is_alive() or not event_queue.empty():
                if token.is_cancelled():
                    cancel_event.set()
                try:
                    event = event_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                event_type = event.get("type")
                if event_type == "progress" and progress_callback is not None:
                    progress_callback(int(event.get("percent", 0)), str(event.get("message", "")))
                elif event_type == "result":
                    process.join(timeout=5)
                    return list(event["records"]), ""
                elif event_type == "error":
                    last_error = f"{event.get('class', 'ProcessError')}: {event.get('error', '')}"
                    process.join(timeout=5)
                    if event.get("class") == "EmbeddingCancelled":
                        raise EmbeddingCancelled("Embedding generation was cancelled.")
                    return None, last_error
            process.join(timeout=5)
            if process.exitcode not in (0, None):
                return None, f"Embedding process exited with code {process.exitcode}."
            return None, last_error or "Embedding process exited without a result."
        finally:
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
            try:
                event_queue.close()
                event_queue.join_thread()
            except Exception:
                pass

