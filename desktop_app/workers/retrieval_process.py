from __future__ import annotations

import multiprocessing as mp
import queue
import time
import traceback
from typing import Any, Callable

from desktop_app.embeddings.embedding_worker import EmbeddingModelUnavailable
from desktop_app.retrieval.query_embedder import QueryEmbedder


class ProcessRetrievalError(RuntimeError):
    pass


def _query_embedding_child_entry(payload: dict[str, Any], event_queue: Any, cancel_event: Any) -> None:
    try:
        if cancel_event.is_set():
            raise ProcessRetrievalError("Query embedding was cancelled.")
        embedder = QueryEmbedder(auto_unload_after_query=True)
        vector = embedder.embed(str(payload["query"]), str(payload["model_name"]))
        event_queue.put({"type": "result", "vector": vector})
    except BaseException as exc:
        event_queue.put(
            {
                "type": "error",
                "error": str(exc),
                "class": exc.__class__.__name__,
                "traceback": traceback.format_exc(),
            }
        )


class ProcessQueryEmbedder:
    def __init__(
        self,
        *,
        process_target: Callable[[dict[str, Any], Any, Any], None] | None = None,
        max_restarts: int = 1,
    ) -> None:
        self.process_target = process_target or _query_embedding_child_entry
        self.max_restarts = max(0, max_restarts)

    def embed(self, query: str, model_name: str) -> list[float]:
        attempts = self.max_restarts + 1
        last_error = ""
        for attempt in range(1, attempts + 1):
            vector, last_error = self._run_once({"query": query, "model_name": model_name})
            if vector is not None:
                return vector
            if attempt < attempts:
                time.sleep(0.2)
        if "EmbeddingModelUnavailable" in last_error:
            raise EmbeddingModelUnavailable(last_error)
        raise ProcessRetrievalError(last_error or "Query embedding process failed.")

    def _run_once(self, payload: dict[str, Any]) -> tuple[list[float] | None, str]:
        context = mp.get_context("spawn")
        event_queue = context.Queue()
        cancel_event = context.Event()
        process = context.Process(target=self.process_target, args=(payload, event_queue, cancel_event), daemon=True)
        process.start()
        last_error = ""
        try:
            while process.is_alive() or not event_queue.empty():
                try:
                    event = event_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                event_type = event.get("type")
                if event_type == "result":
                    process.join(timeout=5)
                    return [float(value) for value in event["vector"]], ""
                if event_type == "error":
                    last_error = f"{event.get('class', 'ProcessError')}: {event.get('error', '')}"
                    process.join(timeout=5)
                    return None, last_error
            process.join(timeout=5)
            if process.exitcode not in (0, None):
                return None, f"Query embedding process exited with code {process.exitcode}."
            return None, last_error or "Query embedding process exited without a result."
        finally:
            cancel_event.set()
            if process.is_alive():
                process.terminate()
                process.join(timeout=5)
            try:
                event_queue.close()
                event_queue.join_thread()
            except Exception:
                pass
