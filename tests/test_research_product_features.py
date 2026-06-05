from __future__ import annotations

import json
import time
from pathlib import Path
from types import SimpleNamespace

from desktop_app.answering.answer_models import Citation
from desktop_app.bookmarks.bookmark_models import Bookmark, BookmarkType
from desktop_app.bookmarks.bookmark_repository import BookmarkRepository
from desktop_app.chat.chat_models import ChatMessage, ChatSession
from desktop_app.chat.chat_repository import ChatRepository
from desktop_app.compare.compare_models import CompareSessionRecord
from desktop_app.compare.compare_repository import CompareRepository
from desktop_app.database.database_manager import DatabaseManager
from desktop_app.evidence.evidence_models import EvidenceHistoryRecord
from desktop_app.evidence.evidence_repository import EvidenceRepository
from desktop_app.exports.research_export_service import ExportFormat, ResearchExportService
from desktop_app.highlights.highlight_models import Highlight, HighlightColor
from desktop_app.highlights.highlight_repository import HighlightRepository
from desktop_app.knowledge.knowledge_models import KnowledgeChunk
from desktop_app.knowledge.knowledge_repository import KnowledgeRepository
from desktop_app.performance.hardware_profiles import HardwareProfileDetector
from desktop_app.performance.runtime_profile_manager import RuntimeProfileManager, RuntimeProfileName
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.providers.provider_router import ProviderRouteKind, ProviderRouter
from desktop_app.providers.provider_benchmark import ProviderBenchmarkRepository, ProviderBenchmarkService
from desktop_app.providers.provider_capabilities import ProviderCapabilityRegistry
from desktop_app.providers.provider_discovery import (
    ProviderDiscoveryResult,
    ProviderDiscoveryService,
    ProviderHealthStatus,
)
from desktop_app.providers.provider_orchestrator import (
    ProviderOrchestrationEngine,
    ProviderRoutingMode,
    ProviderRoutingRequest,
)
from desktop_app.providers.provider_profile import ProviderName
from desktop_app.providers.provider_usage import (
    ProviderUsageRepository,
    ProviderUsageService,
)
from desktop_app.transcripts.transcript_models import Transcript, TranscriptStatus
from desktop_app.transcripts.transcript_repository import TranscriptRepository
from desktop_app.videos.video_metadata import VideoMetadata
from desktop_app.videos.video_model import VideoRecord
from desktop_app.videos.video_repository import VideoRepository


def test_runtime_profile_manager_automatic_selects_low_memory_for_8gb(monkeypatch) -> None:
    monkeypatch.setattr(
        "desktop_app.performance.hardware_profiles.psutil.virtual_memory",
        lambda: SimpleNamespace(total=8 * 1024**3),
    )
    monkeypatch.setattr(
        "desktop_app.performance.hardware_profiles.psutil.cpu_count",
        lambda logical=True: 4,
    )
    monkeypatch.setattr(HardwareProfileDetector, "_gpu_name", lambda self: "No GPU")

    profile = RuntimeProfileManager().resolve("automatic")

    assert profile.name == RuntimeProfileName.LOW_MEMORY
    assert profile.worker_strategy == "starter"
    assert profile.embedding_selection == "small"
    assert profile.whisper_model == "tiny"
    assert profile.cache_policy == "aggressive_unload"


def test_provider_router_smart_routes_by_query_intent() -> None:
    router = ProviderRouter()
    available = {"gemini", "openai", "groq"}

    simple = router.smart_route(query="What is this video about?", available_providers=available)
    research = router.smart_route(query="Compare evidence and citations across videos", available_providers=available)
    long = router.smart_route(query="Write a comprehensive synthesis report " * 8, available_providers=available)
    fast = router.smart_route(query="Quick tl;dr please", available_providers=available, local_available=False)
    manual = router.smart_route(query="anything", manual_override="openai", available_providers=available)

    assert simple.kind == ProviderRouteKind.LOCAL
    assert research.kind == ProviderRouteKind.GEMINI
    assert long.kind == ProviderRouteKind.OPENAI
    assert fast.kind == ProviderRouteKind.GROQ
    assert manual.kind == ProviderRouteKind.OPENAI


def test_provider_discovery_detects_configured_env_without_exposing_secret(tmp_path: Path) -> None:
    env_path = tmp_path / ".env"
    env_path.write_text("OPENAI_API_KEY=secret-value\n", encoding="utf-8")
    service = ProviderDiscoveryService(env_path=str(env_path))

    results = service.discover(check_reachability=False)
    by_name = {result.provider_name: result for result in results}

    assert by_name[ProviderName.OPENAI].configured is True
    assert by_name[ProviderName.OPENAI].status == ProviderHealthStatus.HEALTHY
    assert "secret-value" not in by_name[ProviderName.OPENAI].message
    assert by_name[ProviderName.GEMINI].status == ProviderHealthStatus.UNAVAILABLE


def test_provider_usage_service_tracks_project_costs(tmp_path: Path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Usage Project",
        root_path=str(tmp_path / "project"),
    )
    service = ProviderUsageService(ProviderUsageRepository(database.connection))

    service.record(
        project_id=project.id,
        provider="openai",
        model="gpt-4o-mini",
        task_type="answer_generation",
        token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
        response_time_ms=1200,
    )
    summary = ProviderUsageRepository(database.connection).summarize(project.id)

    assert summary.total_requests == 1
    assert summary.total_tokens == 150
    assert summary.estimated_cost_usd > 0
    assert summary.by_provider["openai"]["requests"] == 1


def _provider_result(provider_name: ProviderName, *, profile_id: str = "") -> ProviderDiscoveryResult:
    capability = ProviderCapabilityRegistry().get(provider_name)
    return ProviderDiscoveryResult(
        provider_name=provider_name,
        status=ProviderHealthStatus.HEALTHY,
        configured=True,
        reachable=capability.is_local,
        healthy=True,
        source="test",
        profile_id=profile_id or provider_name.value,
        model=f"{provider_name.value}-model",
        base_url="http://127.0.0.1:11434" if capability.is_local else "https://example.invalid",
        capability=capability,
        message="test provider",
    )


def test_provider_orchestrator_single_provider_mode_uses_only_provider() -> None:
    engine = ProviderOrchestrationEngine()

    route = engine.route(
        providers=[_provider_result(ProviderName.OPENAI)],
        request=ProviderRoutingRequest(query="Compare evidence", task_type="answering"),
    )

    assert route.kind == ProviderRouteKind.OPENAI
    assert "Single provider mode" in route.reason


def test_provider_orchestrator_local_first_prefers_local_provider() -> None:
    engine = ProviderOrchestrationEngine()

    route = engine.route(
        providers=[_provider_result(ProviderName.OPENAI), _provider_result(ProviderName.OLLAMA)],
        request=ProviderRoutingRequest(
            query="What is covered?",
            task_type="answering",
            mode=ProviderRoutingMode.LOCAL_FIRST,
        ),
    )

    assert route.kind == ProviderRouteKind.OLLAMA


def test_provider_orchestrator_cloud_only_selects_research_capability() -> None:
    engine = ProviderOrchestrationEngine()

    route = engine.route(
        providers=[_provider_result(ProviderName.OPENAI), _provider_result(ProviderName.GEMINI)],
        request=ProviderRoutingRequest(query="Research evidence with citations", task_type="answering"),
    )

    assert route.kind == ProviderRouteKind.GEMINI


def test_provider_orchestrator_mixed_fast_query_prefers_groq() -> None:
    engine = ProviderOrchestrationEngine()

    route = engine.route(
        providers=[
            _provider_result(ProviderName.OPENAI),
            _provider_result(ProviderName.GROQ),
            _provider_result(ProviderName.OLLAMA),
        ],
        request=ProviderRoutingRequest(query="Quick tl;dr please", task_type="answering"),
    )

    assert route.kind == ProviderRouteKind.GROQ


def test_provider_benchmarks_influence_routing(tmp_path: Path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    repository = ProviderBenchmarkRepository(database.connection)
    service = ProviderBenchmarkService(repository)
    service.record_failure(
        provider="groq",
        model="groq-model",
        task_type="answering",
        latency_ms=900,
        error_message="timeout",
    )
    service.record_success(provider="openai", model="openai-model", task_type="answering", latency_ms=100)
    service.record_success(provider="openai", model="openai-model", task_type="answering", latency_ms=100)
    engine = ProviderOrchestrationEngine(benchmark_repository=repository)

    route = engine.route(
        providers=[_provider_result(ProviderName.GROQ), _provider_result(ProviderName.OPENAI)],
        request=ProviderRoutingRequest(query="Quick tl;dr please", task_type="answering"),
    )

    assert route.kind == ProviderRouteKind.OPENAI
    assert "historical success" in route.reason


def test_research_export_service_exports_markdown_json_and_pdf(tmp_path: Path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Export Project",
        root_path=str(tmp_path / "project"),
    )
    chat_repository = ChatRepository(database.connection)
    compare_repository = CompareRepository(database.connection)
    evidence_repository = EvidenceRepository(database.connection)
    bookmark_repository = BookmarkRepository(database.connection)
    highlight_repository = HighlightRepository(database.connection)
    video_path = tmp_path / "lecture.mp4"
    video_path.write_bytes(b"video")
    video = VideoRepository(database.connection).save(
        VideoRecord.create(
            project_id=project.id,
            name=video_path.name,
            file_path=str(video_path),
            file_size=video_path.stat().st_size,
            metadata=VideoMetadata(duration=10.0, fps=30.0, width=1280, height=720),
            thumbnail_path="",
        )
    )
    transcript_repository = TranscriptRepository(database.connection)
    transcript = Transcript.create(
        video_id=video.id,
        model_name="tiny",
        language="en",
        status=TranscriptStatus.COMPLETED,
    )
    transcript_repository.save_transcript(transcript)
    chunk = KnowledgeChunk.create(
        transcript_id=transcript.id,
        start_time=1.0,
        end_time=5.0,
        chunk_text="source-backed finding",
        topic_title="Finding",
        confidence=0.9,
    )
    KnowledgeRepository(database.connection).replace_chunks(transcript.id, [chunk], [])
    session = chat_repository.create_session(ChatSession.create(project_id=project.id, title="Research Chat"))
    citation = Citation(
        citation_id=1,
        source_video="lecture.mp4",
        chunk_id="chunk-1",
        timestamp_start=1.0,
        timestamp_end=5.0,
        confidence=0.9,
    )
    chat_repository.add_message(
        ChatMessage.create(
            session_id=session.id,
            project_id=project.id,
            question="What is the key finding?",
            answer="The key finding is source-backed.",
            citations_json=json.dumps([citation.__dict__]),
            provider="local",
            provider_model="local",
            duration_ms=10,
            token_usage_json="{}",
        )
    )
    compare_repository.save_session(
        CompareSessionRecord(
            id="compare-1",
            project_id=project.id,
            session_name="Compare Session",
            videos_json="[]",
            query="compare topics",
            result_json=json.dumps({"contradictions": [{"summary": "No contradiction"}], "evidence_items": []}),
            created_at=time.time(),
        )
    )
    evidence_repository.save_history(
        [
            EvidenceHistoryRecord(
                id="evidence-1",
                project_id=project.id,
                query="What is the key finding?",
                chunk_id=chunk.chunk_id,
                rank=1,
                similarity_score=0.9,
                confidence_score=0.88,
                created_at=time.time(),
            )
        ]
    )
    bookmark_repository.save(
        Bookmark.create(
            project_id=project.id,
            bookmark_type=BookmarkType.EVIDENCE,
            title="Important Evidence",
            timestamp=1.0,
            chunk_id=chunk.chunk_id,
            source_text="source text",
        )
    )
    highlight_repository.save(
        Highlight.create(
            project_id=project.id,
            highlighted_text="Highlighted insight",
            color=HighlightColor.YELLOW,
            timestamp=2.0,
            chunk_id=chunk.chunk_id,
        )
    )
    service = ResearchExportService(
        chat_repository=chat_repository,
        compare_repository=compare_repository,
        evidence_repository=evidence_repository,
        bookmark_repository=bookmark_repository,
        highlight_repository=highlight_repository,
    )

    markdown = service.export_project_report(project.id, tmp_path / "report.md", ExportFormat.MARKDOWN)
    json_path = service.export_project_report(project.id, tmp_path / "report.json", ExportFormat.JSON)
    pdf_path = service.export_project_report(project.id, tmp_path / "report.pdf", ExportFormat.PDF)

    assert "# Research Report" in markdown.read_text(encoding="utf-8")
    assert json.loads(json_path.read_text(encoding="utf-8"))["title"] == "Research Report"
    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
