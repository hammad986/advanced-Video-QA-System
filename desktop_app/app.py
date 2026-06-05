from __future__ import annotations

import logging
import os
from pathlib import Path

from PySide6.QtCore import QSettings, QTimer
from PySide6.QtWidgets import QApplication

from desktop_app.answering.answer_manager import AnswerManager
from desktop_app.answering.answer_repository import AnswerRepository
from desktop_app.answering.answer_service import AnswerService, ProviderExecutor
from desktop_app.backend.backend_manager import BackendManager
from desktop_app.bookmarks.bookmark_manager import BookmarkManager
from desktop_app.bookmarks.bookmark_repository import BookmarkRepository
from desktop_app.bookmarks.bookmark_service import BookmarkService
from desktop_app.chat.chat_manager import ChatManager
from desktop_app.chat.chat_repository import ChatRepository
from desktop_app.chat.chat_service import ChatService
from desktop_app.chat.chat_session_manager import ChatSessionManager
from desktop_app.compare.compare_manager import CompareManager
from desktop_app.compare.compare_repository import CompareRepository
from desktop_app.compare.compare_service import CompareService
from desktop_app.core.app_constants import AppConstants
from desktop_app.core.app_paths import AppPaths
from desktop_app.core.events import EventBus
from desktop_app.database.database_manager import DatabaseManager
from desktop_app.dialogs.first_run_wizard import FirstRunWizard
from desktop_app.diagnostics.crash_recovery import SessionRecoveryService
from desktop_app.diagnostics.diagnostics_service import DiagnosticsService
from desktop_app.diagnostics.packaging_audit import PackagingAuditService
from desktop_app.embeddings.embedding_manager import EmbeddingManager
from desktop_app.embeddings.model_registry import EmbeddingModelRegistry
from desktop_app.embeddings.embedding_repository import EmbeddingRepository
from desktop_app.embeddings.embedding_service import EmbeddingService
from desktop_app.embeddings.embedding_worker import LocalEmbeddingWorker
from desktop_app.evidence.evidence_manager import EvidenceManager
from desktop_app.evidence.evidence_repository import EvidenceRepository
from desktop_app.evidence.evidence_service import EvidenceService
from desktop_app.exports.research_export_service import ResearchExportService
from desktop_app.highlights.highlight_manager import HighlightManager
from desktop_app.highlights.highlight_repository import HighlightRepository
from desktop_app.highlights.highlight_service import HighlightService
from desktop_app.knowledge.knowledge_manager import KnowledgeManager
from desktop_app.knowledge.knowledge_repository import KnowledgeRepository
from desktop_app.knowledge.knowledge_service import KnowledgeService
from desktop_app.main_window import MainWindow
from desktop_app.performance.hardware_profiles import HardwareProfileDetector
from desktop_app.performance.memory_monitor import MemoryMonitor
from desktop_app.performance.model_benchmarks import ModelBenchmarkHistory
from desktop_app.performance.runtime_profile_manager import RuntimeProfileManager
from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_benchmark import ProviderBenchmarkRepository, ProviderBenchmarkService
from desktop_app.providers.provider_capabilities import ProviderCapabilityRegistry
from desktop_app.providers.provider_discovery import ProviderDiscoveryService
from desktop_app.providers.provider_health import ProviderHealthRepository, ProviderHealthService
from desktop_app.providers.provider_orchestrator import ProviderOrchestrationEngine
from desktop_app.providers.provider_usage import ProviderUsageRepository, ProviderUsageService
from desktop_app.projects.project_manager import ProjectManager
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.retrieval.retrieval_manager import RetrievalManager
from desktop_app.retrieval.retrieval_repository import RetrievalRepository
from desktop_app.retrieval.retrieval_service import RetrievalService
from desktop_app.retrieval.query_embedder import QueryEmbedder
from desktop_app.release.installer_audit import InstallerAuditService
from desktop_app.release.release_candidate_audit import ReleaseCandidateAuditService
from desktop_app.release.update_service import UpdateService, resolve_releases_api_url
from desktop_app.services.task_runner import TaskRunner
from desktop_app.security.credential_migration import EnvCredentialMigrationService
from desktop_app.settings.settings_manager import SettingsManager
from desktop_app.settings.settings_repository import SettingsRepository
from desktop_app.state.app_state import AppState
from desktop_app.styles.theme_manager import ThemeManager
from desktop_app.transcripts.transcript_manager import TranscriptManager
from desktop_app.transcripts.transcript_repository import TranscriptRepository
from desktop_app.transcripts.transcript_service import TranscriptService
from desktop_app.videos.video_manager import VideoManager
from desktop_app.videos.video_repository import VideoRepository
from desktop_app.videos.video_service import VideoService
from desktop_app.vector_store.vector_manager import VectorManager
from desktop_app.vector_store.vector_repository import VectorRepository
from desktop_app.vector_store.vector_service import VectorService
from desktop_app.workers.embedding_process import ProcessEmbeddingWorker
from desktop_app.workers.retrieval_process import ProcessQueryEmbedder
from desktop_app.workers.transcription_process import ProcessTranscriptionWorker
from desktop_app.workers.worker_pool import (
    PooledEmbeddingWorker,
    PooledQueryEmbedder,
    PooledTranscriptionWorker,
    WorkerPoolManager,
)

logger = logging.getLogger(__name__)


class AdvancedVideoQAApp:
    def __init__(self, qt_app: QApplication, paths: AppPaths | None = None) -> None:
        self.qt_app = qt_app
        self.paths = paths or AppPaths.resolve()
        self.paths.ensure()
        self.qt_app.setOrganizationName(AppConstants.ORGANIZATION_NAME)
        self.qt_app.setApplicationName(AppConstants.APPLICATION_NAME)
        self.qt_app.setApplicationVersion(AppConstants.APPLICATION_VERSION)

        self.settings = QSettings(AppConstants.ORGANIZATION_NAME, AppConstants.APPLICATION_NAME)
        self.event_bus = EventBus()
        self.state = AppState(self.event_bus)
        self.task_runner = TaskRunner()
        self.backend_manager = BackendManager(self.state)
        self.database_manager = DatabaseManager(self.paths.database_path)
        self.database_manager.initialize()
        self.embedding_model_registry = EmbeddingModelRegistry.global_instance()
        self.settings_repository = SettingsRepository(self.database_manager.connection)
        self.settings_manager = SettingsManager(
            self.settings_repository,
            default_workspace_path=self.paths.projects_dir,
        )
        self.hardware_profile = HardwareProfileDetector().detect()
        self.runtime_profile_manager = RuntimeProfileManager()
        self.runtime_profile = self.runtime_profile_manager.resolve(self.settings_manager.current.performance_mode)
        self.embedding_model_registry.set_idle_timeout(self.settings_manager.current.embedding_idle_timeout_seconds)
        self.model_isolation_enabled = (
            self.settings_manager.current.low_memory_mode
            or self.hardware_profile.model_isolation_recommended
        )
        self.benchmark_history = ModelBenchmarkHistory(self.paths.app_data_dir / "model_benchmarks.json")
        self.worker_pool: WorkerPoolManager | None = None
        if self.model_isolation_enabled:
            self.worker_pool = WorkerPoolManager.from_profile(
                self.hardware_profile,
                low_memory_mode=self.settings_manager.current.low_memory_mode,
                manual_override=(
                    self.runtime_profile.worker_strategy
                    if self.settings_manager.current.worker_strategy == "auto"
                    else self.settings_manager.current.worker_strategy
                ),
                benchmark_history=self.benchmark_history,
            )
            self.worker_pool.warm_start()
        if self.settings_manager.current.low_memory_mode or self.model_isolation_enabled:
            self.task_runner.thread_pool.setMaxThreadCount(1)
        self.provider_manager = ProviderManager(
            self.database_manager.connection,
            self.settings_manager,
        )
        self.credential_migration_service = EnvCredentialMigrationService(
            self.provider_manager,
            Path.cwd() / ".env",
        )
        self.credential_security_report = self.credential_migration_service.migrate_env_credentials(sanitize_env=True)
        self.provider_capability_registry = ProviderCapabilityRegistry()
        self.provider_benchmark_repository = ProviderBenchmarkRepository(self.database_manager.connection)
        self.provider_benchmark_service = ProviderBenchmarkService(self.provider_benchmark_repository)
        self.provider_health_repository = ProviderHealthRepository(self.database_manager.connection)
        self.provider_health_service = ProviderHealthService(
            repository=self.provider_health_repository,
            provider_manager=self.provider_manager,
            env_path=str(Path.cwd() / ".env"),
        )
        self.provider_discovery_service = ProviderDiscoveryService(
            provider_manager=self.provider_manager,
            capability_registry=self.provider_capability_registry,
        )
        self.provider_orchestrator = ProviderOrchestrationEngine(
            capability_registry=self.provider_capability_registry,
            benchmark_repository=self.provider_benchmark_repository,
        )
        self.project_repository = ProjectRepository(self.database_manager.connection)
        self.project_service = ProjectService(self.project_repository)
        self.project_manager = ProjectManager(self.state, self.project_service, self.settings)
        self.project_manager.restore_last_active_project()
        self.video_repository = VideoRepository(self.database_manager.connection)
        self.video_service = VideoService(self.video_repository, self.project_service)
        self.video_manager = VideoManager(self.video_service, self.task_runner)
        self.transcript_repository = TranscriptRepository(self.database_manager.connection)
        transcript_worker_factory = None
        if self.worker_pool is not None:
            transcript_worker_factory = lambda model: PooledTranscriptionWorker(
                model_name=model,
                pool_manager=self.worker_pool,  # type: ignore[arg-type]
            )
        elif self.model_isolation_enabled:
            transcript_worker_factory = lambda model: ProcessTranscriptionWorker(model_name=model)
        self.transcript_service = TranscriptService(
            self.transcript_repository,
            self.video_manager.get_video,
            worker_factory=transcript_worker_factory,
        )
        self.transcript_manager = TranscriptManager(self.transcript_service, self.task_runner)
        self.knowledge_repository = KnowledgeRepository(self.database_manager.connection)
        self.knowledge_service = KnowledgeService(self.knowledge_repository, self.transcript_repository)
        self.knowledge_manager = KnowledgeManager(self.knowledge_service, self.task_runner)
        self.embedding_repository = EmbeddingRepository(self.database_manager.connection)
        embedding_batch_size = (
            4
            if self.settings_manager.current.low_memory_mode
            else self.runtime_profile.embedding_batch_size
        )
        if self.worker_pool is not None:
            embedding_worker = PooledEmbeddingWorker(
                pool_manager=self.worker_pool,
                batch_size=embedding_batch_size,
            )
        elif self.model_isolation_enabled:
            embedding_worker = ProcessEmbeddingWorker(batch_size=embedding_batch_size)
        else:
            embedding_worker = LocalEmbeddingWorker(
                self.embedding_model_registry,
                batch_size=embedding_batch_size,
                auto_unload_after_generate=self.settings_manager.current.low_memory_mode,
            )
        self.embedding_service = EmbeddingService(
            self.embedding_repository,
            self.knowledge_repository,
            worker=embedding_worker,
        )
        self.embedding_manager = EmbeddingManager(self.embedding_service, self.task_runner)
        self.vector_repository = VectorRepository(self.database_manager.connection)
        self.vector_service = VectorService(self.vector_repository)
        self.vector_manager = VectorManager(self.vector_service, self.task_runner)
        self.retrieval_repository = RetrievalRepository(self.database_manager.connection)
        self.query_embedder = (
            PooledQueryEmbedder(pool_manager=self.worker_pool)
            if self.worker_pool is not None
            else ProcessQueryEmbedder()
            if self.model_isolation_enabled
            else QueryEmbedder(
                self.embedding_model_registry,
                auto_unload_after_query=self.settings_manager.current.low_memory_mode,
            )
        )
        self.retrieval_service = RetrievalService(
            self.retrieval_repository,
            self.vector_repository,
            query_embedder=self.query_embedder,
        )
        self.retrieval_manager = RetrievalManager(self.retrieval_service, self.task_runner)
        self.evidence_repository = EvidenceRepository(self.database_manager.connection)
        self.evidence_service = EvidenceService(self.evidence_repository, self.retrieval_service)
        self.evidence_manager = EvidenceManager(self.evidence_service, self.task_runner)
        self.compare_repository = CompareRepository(self.database_manager.connection)
        self.compare_service = CompareService(self.compare_repository, self.evidence_service)
        self.compare_manager = CompareManager(self.compare_service, self.task_runner)
        self.bookmark_repository = BookmarkRepository(self.database_manager.connection)
        self.bookmark_service = BookmarkService(self.bookmark_repository)
        self.bookmark_manager = BookmarkManager(self.bookmark_service)
        self.highlight_repository = HighlightRepository(self.database_manager.connection)
        self.highlight_service = HighlightService(self.highlight_repository)
        self.highlight_manager = HighlightManager(self.highlight_service)
        self.answer_repository = AnswerRepository(self.database_manager.connection)
        self.provider_executor = ProviderExecutor(self.provider_manager, self.settings_manager)
        self.provider_usage_repository = ProviderUsageRepository(self.database_manager.connection)
        self.provider_usage_service = ProviderUsageService(self.provider_usage_repository)
        self.diagnostics_service = DiagnosticsService()
        self.packaging_audit_service = PackagingAuditService()
        self.installer_audit_service = InstallerAuditService(Path.cwd())
        self.update_service = UpdateService(
            releases_api_url=resolve_releases_api_url(Path.cwd() / ".env"),
            current_version=AppConstants.APPLICATION_VERSION,
        )
        self.release_candidate_audit_service = ReleaseCandidateAuditService(
            self.database_manager.connection,
            video_dir=Path.cwd() / "data" / "videos",
        )
        self.session_recovery_service = SessionRecoveryService(self.paths.app_data_dir / "session_recovery.json")
        self.answer_service = AnswerService(
            self.answer_repository,
            self.evidence_service,
            self.provider_executor,
            provider_usage_service=self.provider_usage_service,
        )
        self.answer_manager = AnswerManager(self.answer_service, self.task_runner)
        self.chat_repository = ChatRepository(self.database_manager.connection)
        self.chat_service = ChatService(self.chat_repository, self.answer_service)
        self.chat_session_manager = ChatSessionManager(self.chat_repository)
        self.chat_manager = ChatManager(self.chat_service, self.task_runner)
        self.export_service = ResearchExportService(
            chat_repository=self.chat_repository,
            compare_repository=self.compare_repository,
            evidence_repository=self.evidence_repository,
            bookmark_repository=self.bookmark_repository,
            highlight_repository=self.highlight_repository,
        )
        self.memory_monitor = MemoryMonitor(self.embedding_model_registry)
        self.embedding_idle_timer = QTimer()
        self.embedding_idle_timer.setInterval(60_000)
        self.embedding_idle_timer.timeout.connect(self.embedding_model_registry.unload_idle_models)
        self.embedding_idle_timer.start()
        self.theme_manager = ThemeManager(self.qt_app, self.settings)
        self.main_window = MainWindow(
            self.state,
            self.event_bus,
            self.settings,
            project_manager=self.project_manager,
            default_projects_dir=self.paths.projects_dir,
            settings_manager=self.settings_manager,
            provider_manager=self.provider_manager,
            video_manager=self.video_manager,
            transcript_manager=self.transcript_manager,
            transcript_repository=self.transcript_repository,
            knowledge_manager=self.knowledge_manager,
            embedding_manager=self.embedding_manager,
            vector_manager=self.vector_manager,
            evidence_manager=self.evidence_manager,
            compare_manager=self.compare_manager,
            bookmark_manager=self.bookmark_manager,
            highlight_manager=self.highlight_manager,
            answer_manager=self.answer_manager,
            chat_manager=self.chat_manager,
            chat_session_manager=self.chat_session_manager,
            memory_monitor=self.memory_monitor,
            hardware_profile=self.hardware_profile,
            provider_health_service=self.provider_health_service,
            provider_health_repository=self.provider_health_repository,
            provider_benchmark_repository=self.provider_benchmark_repository,
            provider_usage_repository=self.provider_usage_repository,
            diagnostics_service=self.diagnostics_service,
            packaging_audit_service=self.packaging_audit_service,
            session_recovery_service=self.session_recovery_service,
            update_service=self.update_service,
        )

        self.event_bus.theme_changed.connect(self.theme_manager.apply_theme)
        self.event_bus.app_closing.connect(self.shutdown)
        self.task_runner.signals.started.connect(self.event_bus.task_started)
        self.task_runner.signals.finished.connect(self.event_bus.task_finished)
        self.task_runner.signals.failed.connect(self.event_bus.task_failed)
        self.task_runner.signals.started.connect(lambda task_id: self.memory_monitor.set_pipeline_status(task_id))
        self.task_runner.signals.finished.connect(lambda *_: self.memory_monitor.set_pipeline_status("Idle"))
        self.task_runner.signals.failed.connect(lambda *_: self.memory_monitor.set_pipeline_status("Idle"))
        self.recovery_timer = QTimer()
        self.recovery_timer.setInterval(10_000)
        self.recovery_timer.timeout.connect(self.main_window.save_recovery_snapshot)
        self.recovery_timer.start()

    def start(self) -> None:
        logger.info("Starting desktop application")
        theme_state = self.theme_manager.load_theme_preference()
        self.state.set_theme_mode(
            theme_state.mode,
            resolved_mode=theme_state.resolved_mode,
            accent_color=theme_state.accent_color,
        )
        self.main_window.show()
        self.main_window.restore_recovery_snapshot()
        if (
            not self.settings_manager.current.first_run_completed
            and os.environ.get("ADVANCED_VIDEO_QA_SKIP_FIRST_RUN", "").lower() not in {"1", "true", "yes"}
        ):
            wizard = FirstRunWizard(
                settings_manager=self.settings_manager,
                provider_manager=self.provider_manager,
                provider_health_service=self.provider_health_service,
                parent=self.main_window,
            )
            wizard.exec()
        self.backend_manager.start()
        self.event_bus.app_started.emit()

    def shutdown(self) -> None:
        logger.info("Shutting down desktop application")
        self.embedding_idle_timer.stop()
        self.recovery_timer.stop()
        self.main_window.save_recovery_snapshot()
        if self.worker_pool is not None:
            self.worker_pool.shutdown()
        self.backend_manager.stop()
        self.task_runner.shutdown()
        self.embedding_model_registry.unload_idle_models(force=True)
