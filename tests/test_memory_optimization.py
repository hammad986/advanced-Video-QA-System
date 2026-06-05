from __future__ import annotations

import time
from pathlib import Path
from types import SimpleNamespace

from desktop_app.embeddings.embedding_worker import LocalEmbeddingWorker
from desktop_app.embeddings.embedding_models import EmbeddingRecord
from desktop_app.embeddings.model_registry import EmbeddingModelRegistry
from desktop_app.knowledge.knowledge_models import KnowledgeChunk
from desktop_app.performance.hardware_profiles import HardwareProfileDetector
from desktop_app.performance.model_benchmarks import ModelBenchmarkHistory
from desktop_app.providers.provider_router import ProviderRouteKind, ProviderRouter
from desktop_app.retrieval.query_embedder import QueryEmbedder
from desktop_app.transcripts.transcript_models import TranscriptionResult, TranscriptionSegmentResult
from desktop_app.transcripts.transcription_worker import CancellationToken, TranscriptionWorker
from desktop_app.workers.embedding_process import ProcessEmbeddingWorker
from desktop_app.workers.retrieval_process import ProcessQueryEmbedder
from desktop_app.workers.transcription_process import ProcessTranscriptionWorker
from desktop_app.workers.worker_pool import (
    WorkerPoolManager,
    WorkerPoolStrategy,
    worker_strategy_for_profile,
)


def _fake_embedding_process_target(payload, event_queue, cancel_event) -> None:
    _ = cancel_event
    chunks = list(payload["chunks"])
    event_queue.put({"type": "progress", "percent": 50, "message": "fake process progress"})
    event_queue.put(
        {
            "type": "result",
            "records": [
                EmbeddingRecord.create(
                    chunk_id=chunk.chunk_id,
                    model_name=str(payload["model_name"]),
                    vector=[1.0, 2.0, 3.0],
                )
                for chunk in chunks
            ],
        }
    )


def _fake_query_process_target(payload, event_queue, cancel_event) -> None:
    _ = payload, cancel_event
    event_queue.put({"type": "result", "vector": [0.1, 0.2, 0.3]})


def _fake_transcription_process_target(payload, event_queue, cancel_event) -> None:
    _ = payload, cancel_event
    event_queue.put({"type": "progress", "percent": 60, "message": "fake transcription"})
    event_queue.put(
        {
            "type": "result",
            "result": TranscriptionResult(
                language="en",
                segments=[TranscriptionSegmentResult(0.0, 1.0, "hello", 0.9)],
            ),
        }
    )


def _fake_warm_retrieval_target(command_queue, event_queue, cancel_event, idle_timeout) -> None:
    _ = cancel_event, idle_timeout
    while True:
        command = command_queue.get(timeout=5)
        if command.get("action") == "shutdown":
            break
        event_queue.put(
            {
                "job_id": command["job_id"],
                "type": "result",
                "vector": [0.4, 0.5, 0.6],
                "duration_seconds": 0.01,
            }
        )


def _unused_warm_target(command_queue, event_queue, cancel_event, idle_timeout) -> None:
    _ = event_queue, cancel_event, idle_timeout
    command = command_queue.get(timeout=5)
    if command.get("action") != "shutdown":
        raise RuntimeError("unused warm target was invoked")


def test_embedding_registry_unloads_idle_models() -> None:
    registry = EmbeddingModelRegistry()
    registry._models["idle-model"] = object()
    registry._last_used["idle-model"] = time.monotonic() - 20
    registry.set_idle_timeout(1)

    unloaded = registry.unload_idle_models()

    assert unloaded == ["idle-model"]
    assert registry.loaded_model_count() == 0
    assert registry.loaded_model_names() == []


def test_embedding_registry_force_unload_ignores_idle_time() -> None:
    registry = EmbeddingModelRegistry()
    registry._models["active-model"] = object()
    registry._last_used["active-model"] = time.monotonic()
    registry.set_idle_timeout(600)

    unloaded = registry.unload_idle_models(force=True)

    assert unloaded == ["active-model"]
    assert registry.loaded_model_count() == 0


class _FakeVector(list[float]):
    def tolist(self) -> list[float]:
        return list(self)


class _FakeEmbeddingRegistry:
    def __init__(self) -> None:
        self.batch_size: int | None = None
        self.unloaded_model: str | None = None

    def get_model(self, model_name: str) -> object:
        return object()

    def encode(
        self,
        texts: list[str] | str,
        model_name: str,
        batch_size: int = 32,
    ) -> list[_FakeVector] | _FakeVector:
        self.batch_size = batch_size
        if isinstance(texts, str):
            return _FakeVector([1.0, 2.0, 3.0])
        return [_FakeVector([1.0, 2.0, 3.0]) for _ in texts]

    def unload_model(self, model_name: str) -> bool:
        self.unloaded_model = model_name
        return True


def test_local_embedding_worker_uses_low_memory_batch_and_auto_unload() -> None:
    registry = _FakeEmbeddingRegistry()
    worker = LocalEmbeddingWorker(
        model_registry=registry,
        batch_size=4,
        auto_unload_after_generate=True,
    )
    chunk = KnowledgeChunk(
        chunk_id="chunk-1",
        transcript_id="transcript-1",
        start_time=0.0,
        end_time=10.0,
        chunk_text="This is a test chunk.",
        topic_title="Test Topic",
        confidence=0.8,
        word_count=5,
        created_at=1.0,
    )

    records = worker.generate([chunk], "BAAI/bge-small-en-v1.5")

    assert registry.batch_size == 4
    assert registry.unloaded_model == "BAAI/bge-small-en-v1.5"
    assert len(records) == 1
    assert records[0].dimension == 3


def test_process_embedding_worker_uses_ipc_progress_and_result() -> None:
    progress_events: list[tuple[int, str]] = []
    worker = ProcessEmbeddingWorker(
        batch_size=4,
        process_target=_fake_embedding_process_target,
        max_restarts=0,
    )
    chunk = KnowledgeChunk(
        chunk_id="chunk-1",
        transcript_id="transcript-1",
        start_time=0.0,
        end_time=10.0,
        chunk_text="This is a test chunk.",
        topic_title="Test Topic",
        confidence=0.8,
        word_count=5,
        created_at=1.0,
    )

    records = worker.generate(
        [chunk],
        "BAAI/bge-small-en-v1.5",
        progress_callback=lambda percent, message: progress_events.append((percent, message)),
    )

    assert len(records) == 1
    assert records[0].chunk_id == "chunk-1"
    assert progress_events == [(50, "fake process progress")]


def test_process_query_embedder_returns_vector_from_child_process() -> None:
    embedder = ProcessQueryEmbedder(
        process_target=_fake_query_process_target,
        max_restarts=0,
    )

    vector = embedder.embed("What is covered?", "BAAI/bge-small-en-v1.5")

    assert vector == [0.1, 0.2, 0.3]


def test_process_transcription_worker_returns_result_from_child_process(tmp_path: Path) -> None:
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"fake-video")
    progress_events: list[tuple[int, str]] = []
    worker = ProcessTranscriptionWorker(
        model_name="tiny",
        process_target=_fake_transcription_process_target,
        max_restarts=0,
    )

    result = worker.run(
        video_path,
        CancellationToken(),
        progress=lambda percent, message: progress_events.append((percent, message)),
    )

    assert result.language == "en"
    assert result.segments[0].text == "hello"
    assert progress_events == [(60, "fake transcription")]


def test_worker_pool_reuses_warm_retrieval_process(tmp_path: Path) -> None:
    history = ModelBenchmarkHistory(tmp_path / "benchmarks.json")
    pool = WorkerPoolManager(
        strategy=WorkerPoolStrategy(
            name="test",
            keep_transcription_warm=False,
            keep_embedding_warm=False,
            keep_retrieval_warm=True,
            idle_timeout_seconds=30,
        ),
        benchmark_history=history,
        transcription_target=_unused_warm_target,
        embedding_target=_unused_warm_target,
        retrieval_target=_fake_warm_retrieval_target,
    )
    try:
        first = pool.embed_query(query="first", model_name="BAAI/bge-small-en-v1.5")
        second = pool.embed_query(query="second", model_name="BAAI/bge-small-en-v1.5")
        retrieval_status = {status.name: status for status in pool.statuses()}["retrieval"]
        records = history.list_records()
    finally:
        pool.shutdown()

    assert first == [0.4, 0.5, 0.6]
    assert second == [0.4, 0.5, 0.6]
    assert retrieval_status.cold_starts == 1
    assert retrieval_status.warm_reuses == 1
    assert [record.cold_start for record in records] == [True, False]


def test_provider_router_prefers_local_then_selected_cloud() -> None:
    router = ProviderRouter()

    local_route = router.route(task_type="answering", local_available=True)
    cloud_route = router.route(task_type="answering", preferred_provider="openai", preferred_model="gpt-4o-mini")

    assert local_route.kind == ProviderRouteKind.LOCAL
    assert cloud_route.kind == ProviderRouteKind.OPENAI
    assert cloud_route.model_name == "gpt-4o-mini"


def test_query_embedder_can_auto_unload_after_query_embedding() -> None:
    registry = _FakeEmbeddingRegistry()
    embedder = QueryEmbedder(
        model_registry=registry,
        auto_unload_after_query=True,
    )

    vector = embedder.embed("What is covered?", "BAAI/bge-small-en-v1.5")

    assert vector == [1.0, 2.0, 3.0]
    assert registry.unloaded_model == "BAAI/bge-small-en-v1.5"


class _FakeTranscriptionEngine:
    def __init__(self) -> None:
        self.unloaded = False

    def transcribe(self, audio_path: Path, token: CancellationToken) -> TranscriptionResult:
        return TranscriptionResult(language="en", segments=[])

    def unload(self) -> None:
        self.unloaded = True


class _TestTranscriptionWorker(TranscriptionWorker):
    def extract_audio(self, video_path: Path, audio_path: Path, token: CancellationToken) -> Path:
        audio_path.write_bytes(b"fake-audio")
        return audio_path


def test_transcription_worker_unloads_engine_after_run(tmp_path: Path) -> None:
    engine = _FakeTranscriptionEngine()
    video_path = tmp_path / "video.mp4"
    video_path.write_bytes(b"fake-video")
    worker = _TestTranscriptionWorker(
        model_name="tiny",
        engine_factory=lambda model_name: engine,
    )

    result = worker.run(video_path, CancellationToken())

    assert result.language == "en"
    assert engine.unloaded is True


def test_hardware_profile_detector_selects_starter_for_8gb(monkeypatch) -> None:
    monkeypatch.setattr(
        "desktop_app.performance.hardware_profiles.psutil.virtual_memory",
        lambda: SimpleNamespace(total=8 * 1024**3),
    )
    monkeypatch.setattr(
        "desktop_app.performance.hardware_profiles.psutil.cpu_count",
        lambda logical=True: 4,
    )
    monkeypatch.setattr(HardwareProfileDetector, "_gpu_name", lambda self: "No GPU")

    profile = HardwareProfileDetector().detect()

    assert profile.name == "Starter"
    assert profile.whisper_model == "tiny"
    assert profile.embedding_selection == "small"
    assert profile.embedding_batch_size == 4
    assert profile.low_memory_recommended is True
    assert profile.model_isolation_recommended is True

    strategy = worker_strategy_for_profile(profile, low_memory_mode=True)
    assert strategy.name == "starter"
    assert strategy.keep_retrieval_warm is True
    assert strategy.idle_timeout_seconds == 45


def test_hardware_profile_detector_selects_standard_for_16gb(monkeypatch) -> None:
    monkeypatch.setattr(
        "desktop_app.performance.hardware_profiles.psutil.virtual_memory",
        lambda: SimpleNamespace(total=16 * 1024**3),
    )
    monkeypatch.setattr(
        "desktop_app.performance.hardware_profiles.psutil.cpu_count",
        lambda logical=True: 8,
    )
    monkeypatch.setattr(HardwareProfileDetector, "_gpu_name", lambda self: "No GPU")

    profile = HardwareProfileDetector().detect()

    assert profile.name == "Standard"
    assert profile.whisper_model == "small"
    assert profile.embedding_selection == "base"
    assert profile.model_isolation_recommended is True

    strategy = worker_strategy_for_profile(profile, low_memory_mode=False)
    assert strategy.name == "standard"
    assert strategy.keep_retrieval_warm is True
    assert strategy.keep_embedding_warm is False


def test_hardware_profile_detector_selects_advanced_for_32gb(monkeypatch) -> None:
    monkeypatch.setattr(
        "desktop_app.performance.hardware_profiles.psutil.virtual_memory",
        lambda: SimpleNamespace(total=32 * 1024**3),
    )
    monkeypatch.setattr(
        "desktop_app.performance.hardware_profiles.psutil.cpu_count",
        lambda logical=True: 16,
    )
    monkeypatch.setattr(HardwareProfileDetector, "_gpu_name", lambda self: "No GPU")

    profile = HardwareProfileDetector().detect()

    assert profile.name == "Advanced"
    assert profile.whisper_model == "medium"
    assert profile.embedding_selection == "large"

    strategy = worker_strategy_for_profile(profile, low_memory_mode=False)
    assert strategy.keep_retrieval_warm is True
    assert strategy.keep_embedding_warm is True
