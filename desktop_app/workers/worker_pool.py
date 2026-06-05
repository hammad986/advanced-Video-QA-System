from __future__ import annotations

import multiprocessing as mp
import queue
import tempfile
import time
import traceback
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from desktop_app.embeddings.embedding_models import EmbeddingRecord
from desktop_app.embeddings.embedding_worker import CancellationToken as EmbeddingCancellationToken
from desktop_app.embeddings.embedding_worker import EmbeddingCancelled, EmbeddingError, LocalEmbeddingWorker
from desktop_app.core.frozen_runtime import configure_frozen_runtime_paths
from desktop_app.embeddings.model_registry import EmbeddingModelRegistry
from desktop_app.knowledge.knowledge_models import KnowledgeChunk
from desktop_app.performance.hardware_profiles import HardwareProfile
from desktop_app.performance.model_benchmarks import ModelBenchmarkHistory
from desktop_app.retrieval.query_embedder import QueryEmbedder
from desktop_app.transcripts.transcript_models import TranscriptionResult
from desktop_app.transcripts.transcription_worker import (
    CancellationToken as TranscriptionCancellationToken,
)
from desktop_app.transcripts.transcription_worker import (
    TranscriptionCancelled,
    TranscriptionError,
    TranscriptionWorker,
    WhisperTranscriptionEngine,
)


class WorkerPoolError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkerPoolStrategy:
    name: str
    keep_transcription_warm: bool
    keep_embedding_warm: bool
    keep_retrieval_warm: bool
    idle_timeout_seconds: int


@dataclass(frozen=True)
class WorkerStatus:
    name: str
    running: bool
    pid: int | None
    cold_starts: int
    warm_reuses: int
    last_duration_seconds: float


class _ProcessTranscriptionToken:
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


class _ProcessEmbeddingToken(EmbeddingCancellationToken):
    def __init__(self, cancel_event: Any) -> None:
        self.cancel_event = cancel_event

    def cancel(self) -> None:
        self.cancel_event.set()

    def is_cancelled(self) -> bool:
        return bool(self.cancel_event.is_set())


def warm_transcription_worker_entry(command_queue: Any, event_queue: Any, cancel_event: Any, idle_timeout: int) -> None:
    configure_frozen_runtime_paths()
    engine: WhisperTranscriptionEngine | None = None
    engine_model = ""
    helper_by_model: dict[str, TranscriptionWorker] = {}
    try:
        while True:
            try:
                command = command_queue.get(timeout=max(1, idle_timeout))
            except queue.Empty:
                break
            if command.get("action") == "shutdown":
                break
            job_id = str(command["job_id"])
            started = time.perf_counter()
            try:
                model_name = str(command["model_name"])
                video_path = Path(str(command["video_path"]))
                helper = helper_by_model.setdefault(model_name, TranscriptionWorker(model_name=model_name))
                if engine is None or engine_model != model_name:
                    if engine is not None:
                        engine.unload()
                    engine = WhisperTranscriptionEngine(model_name)
                    engine_model = model_name
                token = _ProcessTranscriptionToken(cancel_event)
                with tempfile.TemporaryDirectory(prefix="avqa_warm_transcript_") as temp_dir:
                    audio_path = Path(temp_dir) / f"{video_path.stem}.wav"
                    event_queue.put({"job_id": job_id, "type": "progress", "percent": 5, "message": "Preparing audio"})
                    helper.extract_audio(video_path, audio_path, token)
                    event_queue.put({"job_id": job_id, "type": "progress", "percent": 35, "message": "Audio extracted"})
                    result = engine.transcribe(audio_path, token)
                event_queue.put(
                    {
                        "job_id": job_id,
                        "type": "result",
                        "result": result,
                        "duration_seconds": time.perf_counter() - started,
                    }
                )
            except BaseException as exc:
                event_queue.put(_error_event(job_id, exc))
    finally:
        if engine is not None:
            engine.unload()


def warm_embedding_worker_entry(command_queue: Any, event_queue: Any, cancel_event: Any, idle_timeout: int) -> None:
    configure_frozen_runtime_paths()
    registry = EmbeddingModelRegistry()
    try:
        worker = LocalEmbeddingWorker(registry, auto_unload_after_generate=False)
        while True:
            try:
                command = command_queue.get(timeout=max(1, idle_timeout))
            except queue.Empty:
                break
            if command.get("action") == "shutdown":
                break
            job_id = str(command["job_id"])
            started = time.perf_counter()
            try:
                worker.batch_size = max(1, int(command.get("batch_size", 4)))
                token = _ProcessEmbeddingToken(cancel_event)

                def progress(percent: int, message: str) -> None:
                    event_queue.put({"job_id": job_id, "type": "progress", "percent": percent, "message": message})

                records = worker.generate(
                    list(command["chunks"]),
                    str(command["model_name"]),
                    cancellation_token=token,
                    progress_callback=progress,
                )
                event_queue.put(
                    {
                        "job_id": job_id,
                        "type": "result",
                        "records": records,
                        "duration_seconds": time.perf_counter() - started,
                    }
                )
            except BaseException as exc:
                event_queue.put(_error_event(job_id, exc))
    finally:
        registry.clear()


def warm_retrieval_worker_entry(command_queue: Any, event_queue: Any, cancel_event: Any, idle_timeout: int) -> None:
    configure_frozen_runtime_paths()
    registry = EmbeddingModelRegistry()
    try:
        embedder = QueryEmbedder(registry, auto_unload_after_query=False)
        while True:
            try:
                command = command_queue.get(timeout=max(1, idle_timeout))
            except queue.Empty:
                break
            if command.get("action") == "shutdown":
                break
            job_id = str(command["job_id"])
            started = time.perf_counter()
            try:
                if cancel_event.is_set():
                    raise WorkerPoolError("Query embedding was cancelled.")
                vector = embedder.embed(str(command["query"]), str(command["model_name"]))
                event_queue.put(
                    {
                        "job_id": job_id,
                        "type": "result",
                        "vector": vector,
                        "duration_seconds": time.perf_counter() - started,
                    }
                )
            except BaseException as exc:
                event_queue.put(_error_event(job_id, exc))
    finally:
        registry.clear()


def _error_event(job_id: str, exc: BaseException) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "type": "error",
        "class": exc.__class__.__name__,
        "error": str(exc),
        "traceback": traceback.format_exc(),
    }


class _WarmProcessClient:
    def __init__(
        self,
        *,
        name: str,
        target: Callable[[Any, Any, Any, int], None],
        idle_timeout_seconds: int,
        benchmark_history: ModelBenchmarkHistory | None = None,
    ) -> None:
        self.name = name
        self.target = target
        self.idle_timeout_seconds = max(1, idle_timeout_seconds)
        self.benchmark_history = benchmark_history
        self.context = mp.get_context("spawn")
        self.command_queue: Any | None = None
        self.event_queue: Any | None = None
        self.cancel_event: Any | None = None
        self.process: Any | None = None
        self.cold_starts = 0
        self.warm_reuses = 0
        self.last_duration_seconds = 0.0
        self._request_count = 0

    def request(
        self,
        *,
        action: str,
        payload: dict[str, Any],
        model_name: str,
        operation: str,
        progress_callback: Callable[[int, str], None] | None = None,
        is_cancelled: Callable[[], bool] | None = None,
    ) -> dict[str, Any]:
        process_was_running = self.is_running()
        cold_start = not process_was_running or self._request_count == 0
        if not process_was_running:
            self.start()
        if cold_start:
            self.cold_starts += 1
        else:
            self.warm_reuses += 1
        self._request_count += 1
        if self.cancel_event is not None:
            self.cancel_event.clear()
        job_id = uuid.uuid4().hex
        command = {"job_id": job_id, "action": action, **payload}
        assert self.command_queue is not None
        assert self.event_queue is not None
        self.command_queue.put(command)
        started = time.perf_counter()
        while self.is_running() or not self.event_queue.empty():
            if is_cancelled is not None and is_cancelled() and self.cancel_event is not None:
                self.cancel_event.set()
            try:
                event = self.event_queue.get(timeout=0.1)
            except queue.Empty:
                continue
            if str(event.get("job_id")) != job_id:
                continue
            if event.get("type") == "progress" and progress_callback is not None:
                progress_callback(int(event.get("percent", 0)), str(event.get("message", "")))
            elif event.get("type") == "result":
                self.last_duration_seconds = time.perf_counter() - started
                self._record_benchmark(model_name, operation, cold_start, self.last_duration_seconds)
                return event
            elif event.get("type") == "error":
                self._record_benchmark(model_name, operation, cold_start, time.perf_counter() - started)
                self.restart()
                error_class = event.get("class", "WorkerPoolError")
                error_text = event.get("error", "")
                if error_class in {"TranscriptionCancelled", "EmbeddingCancelled"}:
                    raise WorkerPoolError(f"{error_class}: {error_text}")
                raise WorkerPoolError(f"{error_class}: {error_text}")
        self.restart()
        raise WorkerPoolError(f"{self.name} worker exited before returning a result.")

    def start(self) -> None:
        self.command_queue = self.context.Queue()
        self.event_queue = self.context.Queue()
        self.cancel_event = self.context.Event()
        self.process = self.context.Process(
            target=self.target,
            args=(self.command_queue, self.event_queue, self.cancel_event, self.idle_timeout_seconds),
            daemon=True,
        )
        self.process.start()

    def is_running(self) -> bool:
        return self.process is not None and self.process.is_alive()

    def restart(self) -> None:
        self.stop(force=True)
        self.start()
        self.cold_starts += 1

    def stop(self, *, force: bool = False) -> None:
        if self.command_queue is not None and self.is_running() and not force:
            try:
                self.command_queue.put({"action": "shutdown"})
            except Exception:
                pass
        if self.process is not None:
            if force and self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=5)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=5)
        for ipc_object in (self.command_queue, self.event_queue):
            try:
                if ipc_object is not None:
                    ipc_object.close()
                    ipc_object.join_thread()
            except Exception:
                pass
        self.command_queue = None
        self.event_queue = None
        self.cancel_event = None
        self.process = None
        self._request_count = 0

    def status(self) -> WorkerStatus:
        return WorkerStatus(
            name=self.name,
            running=self.is_running(),
            pid=int(self.process.pid) if self.process is not None and self.process.pid is not None else None,
            cold_starts=self.cold_starts,
            warm_reuses=self.warm_reuses,
            last_duration_seconds=self.last_duration_seconds,
        )

    def _record_benchmark(self, model_name: str, operation: str, cold_start: bool, duration_seconds: float) -> None:
        if self.benchmark_history is not None:
            self.benchmark_history.append(
                worker_name=self.name,
                model_name=model_name,
                operation=operation,
                cold_start=cold_start,
                duration_seconds=duration_seconds,
            )


class WorkerPoolManager:
    def __init__(
        self,
        *,
        strategy: WorkerPoolStrategy,
        benchmark_history: ModelBenchmarkHistory | None = None,
        transcription_target: Callable[[Any, Any, Any, int], None] = warm_transcription_worker_entry,
        embedding_target: Callable[[Any, Any, Any, int], None] = warm_embedding_worker_entry,
        retrieval_target: Callable[[Any, Any, Any, int], None] = warm_retrieval_worker_entry,
    ) -> None:
        self.strategy = strategy
        self.transcription = _WarmProcessClient(
            name="transcription",
            target=transcription_target,
            idle_timeout_seconds=strategy.idle_timeout_seconds if strategy.keep_transcription_warm else 1,
            benchmark_history=benchmark_history,
        )
        self.embedding = _WarmProcessClient(
            name="embedding",
            target=embedding_target,
            idle_timeout_seconds=strategy.idle_timeout_seconds if strategy.keep_embedding_warm else 1,
            benchmark_history=benchmark_history,
        )
        self.retrieval = _WarmProcessClient(
            name="retrieval",
            target=retrieval_target,
            idle_timeout_seconds=strategy.idle_timeout_seconds if strategy.keep_retrieval_warm else 1,
            benchmark_history=benchmark_history,
        )

    @classmethod
    def from_profile(
        cls,
        profile: HardwareProfile,
        *,
        low_memory_mode: bool,
        manual_override: str = "auto",
        benchmark_history: ModelBenchmarkHistory | None = None,
    ) -> "WorkerPoolManager":
        return cls(
            strategy=worker_strategy_for_profile(profile, low_memory_mode, manual_override),
            benchmark_history=benchmark_history,
        )

    def warm_start(self) -> None:
        if self.strategy.keep_transcription_warm:
            self.transcription.start()
        if self.strategy.keep_embedding_warm:
            self.embedding.start()
        if self.strategy.keep_retrieval_warm:
            self.retrieval.start()

    def transcribe(
        self,
        *,
        video_path: Path,
        model_name: str,
        is_cancelled: Callable[[], bool],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> TranscriptionResult:
        event = self.transcription.request(
            action="transcribe",
            payload={"video_path": str(video_path), "model_name": model_name},
            model_name=model_name,
            operation="transcription",
            progress_callback=progress_callback,
            is_cancelled=is_cancelled,
        )
        return event["result"]

    def generate_embeddings(
        self,
        *,
        chunks: list[KnowledgeChunk],
        model_name: str,
        batch_size: int,
        is_cancelled: Callable[[], bool],
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> list[EmbeddingRecord]:
        event = self.embedding.request(
            action="embed_chunks",
            payload={"chunks": chunks, "model_name": model_name, "batch_size": batch_size},
            model_name=model_name,
            operation="embedding",
            progress_callback=progress_callback,
            is_cancelled=is_cancelled,
        )
        return list(event["records"])

    def embed_query(self, *, query: str, model_name: str) -> list[float]:
        event = self.retrieval.request(
            action="embed_query",
            payload={"query": query, "model_name": model_name},
            model_name=model_name,
            operation="query_embedding",
        )
        return [float(value) for value in event["vector"]]

    def statuses(self) -> list[WorkerStatus]:
        return [self.transcription.status(), self.embedding.status(), self.retrieval.status()]

    def shutdown(self) -> None:
        self.transcription.stop()
        self.embedding.stop()
        self.retrieval.stop()


def worker_strategy_for_profile(
    profile: HardwareProfile,
    low_memory_mode: bool,
    manual_override: str = "auto",
) -> WorkerPoolStrategy:
    selected = manual_override.strip().lower() if manual_override else "auto"
    if selected == "auto":
        selected = profile.name.lower()
    if low_memory_mode:
        selected = "starter"
    if selected == "starter":
        return WorkerPoolStrategy("starter", True, True, True, 45)
    if selected == "standard":
        return WorkerPoolStrategy("standard", False, False, True, 600)
    if selected == "advanced":
        return WorkerPoolStrategy("advanced", False, True, True, 900)
    if selected == "workstation":
        return WorkerPoolStrategy("workstation", True, True, True, 1800)
    return WorkerPoolStrategy("isolated_cold", False, False, False, 1)


class PooledTranscriptionWorker:
    def __init__(self, *, model_name: str, pool_manager: WorkerPoolManager) -> None:
        self.model_name = model_name
        self.pool_manager = pool_manager

    def run(
        self,
        video_path: Path,
        token: TranscriptionCancellationToken,
        progress: Callable[[int, str], None] | None = None,
    ) -> TranscriptionResult:
        try:
            return self.pool_manager.transcribe(
                video_path=video_path,
                model_name=self.model_name,
                is_cancelled=lambda: bool(token.is_cancelled),
                progress_callback=progress,
            )
        except WorkerPoolError as exc:
            if "TranscriptionCancelled" in str(exc):
                raise TranscriptionCancelled("Transcription was cancelled.") from exc
            raise TranscriptionError(str(exc)) from exc


class PooledEmbeddingWorker:
    def __init__(self, *, pool_manager: WorkerPoolManager, batch_size: int) -> None:
        self.pool_manager = pool_manager
        self.batch_size = max(1, batch_size)

    def generate(
        self,
        chunks: list[KnowledgeChunk],
        model_name: str,
        cancellation_token: EmbeddingCancellationToken | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> list[EmbeddingRecord]:
        token = cancellation_token or EmbeddingCancellationToken()
        try:
            return self.pool_manager.generate_embeddings(
                chunks=chunks,
                model_name=model_name,
                batch_size=self.batch_size,
                is_cancelled=token.is_cancelled,
                progress_callback=progress_callback,
            )
        except WorkerPoolError as exc:
            if "EmbeddingCancelled" in str(exc):
                raise EmbeddingCancelled("Embedding generation was cancelled.") from exc
            raise EmbeddingError(str(exc)) from exc


class PooledQueryEmbedder:
    def __init__(self, *, pool_manager: WorkerPoolManager) -> None:
        self.pool_manager = pool_manager

    def embed(self, query: str, model_name: str) -> list[float]:
        return self.pool_manager.embed_query(query=query, model_name=model_name)
