from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QSettings, Qt
from PySide6.QtGui import QAction, QCloseEvent
from PySide6.QtWidgets import (
    QLabel,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMenu,
    QMessageBox,
    QDialog,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from desktop_app.answering.answer_manager import AnswerManager
from desktop_app.answering.answer_models import AnswerJobState, AnswerResult, AnswerStatus, Citation
from desktop_app.bookmarks.bookmark_manager import BookmarkManager
from desktop_app.bookmarks.bookmark_models import Bookmark
from desktop_app.chat.chat_manager import ChatManager
from desktop_app.chat.chat_models import ChatJobState, ChatMessage
from desktop_app.chat.chat_session_manager import ChatSessionManager
from desktop_app.compare.compare_manager import CompareManager
from desktop_app.compare.compare_models import CompareJobState, CompareResult, CompareStatus
from desktop_app.core.app_constants import AppConstants
from desktop_app.core.events import EventBus
from desktop_app.dialogs.provider_management_dialog import ProviderManagementDialog
from desktop_app.dialogs.project_dialogs import CreateProjectDialog, OpenProjectDialog
from desktop_app.dialogs.settings_dialog import SettingsDialog
from desktop_app.diagnostics.crash_recovery import SessionRecoveryService
from desktop_app.diagnostics.diagnostics_service import DiagnosticsService, DiagnosticsSnapshot
from desktop_app.diagnostics.packaging_audit import PackagingAuditService
from desktop_app.embeddings.embedding_manager import EmbeddingManager
from desktop_app.embeddings.embedding_models import EmbeddingJobState, EmbeddingStatus
from desktop_app.evidence.evidence_manager import EvidenceManager
from desktop_app.evidence.evidence_models import EvidenceItem, EvidenceJobState, EvidenceResult, EvidenceStatus
from desktop_app.highlights.highlight_manager import HighlightManager
from desktop_app.highlights.highlight_models import Highlight, HighlightColor
from desktop_app.knowledge.knowledge_manager import KnowledgeManager
from desktop_app.performance.hardware_profiles import HardwareProfile
from desktop_app.performance.memory_monitor import MemoryMonitor
from desktop_app.player.frame_provider import SnapshotError
from desktop_app.player.video_player import VideoPlayer
from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_benchmark import ProviderBenchmarkRepository
from desktop_app.providers.provider_health import ProviderHealthRepository, ProviderHealthResult, ProviderHealthService
from desktop_app.providers.provider_usage import ProviderUsageRepository
from desktop_app.projects.project_manager import ProjectManager
from desktop_app.release.update_service import UpdateService
from desktop_app.settings.settings_manager import SettingsManager
from desktop_app.state.app_state import AppState
from desktop_app.state.backend_state import BackendState, BackendStatus
from desktop_app.state.theme_state import ThemeMode, ThemeState
from desktop_app.transcripts.transcript_manager import TranscriptManager
from desktop_app.transcripts.transcript_models import TranscriptJobState, TranscriptStatus
from desktop_app.transcripts.transcript_repository import TranscriptRepository
from desktop_app.transcript_viewer.transcript_viewer_widget import TranscriptViewerWidget
from desktop_app.widgets.chat_workspace import ChatWorkspaceWidget
from desktop_app.widgets.bookmark_panel import BookmarkPanelWidget
from desktop_app.widgets.compare_workspace import CompareWorkspaceWidget
from desktop_app.widgets.highlight_panel import HighlightPanelWidget
from desktop_app.widgets.memory_dashboard import MemoryDashboardWidget
from desktop_app.widgets.diagnostics_panel import DiagnosticsPanelWidget
from desktop_app.widgets.provider_dashboard import ProviderDashboardWidget
from desktop_app.widgets.provider_selector import ProviderSelector
from desktop_app.widgets.embedding_panel import EmbeddingPanelWidget
from desktop_app.widgets.knowledge_summary import KnowledgeSummaryWidget
from desktop_app.widgets.project_switcher import ProjectSwitcher
from desktop_app.widgets.transcript_queue import TranscriptQueueWidget
from desktop_app.widgets.video_library import VideoLibraryWidget
from desktop_app.widgets.vector_index_panel import VectorIndexPanelWidget
from desktop_app.widgets.evidence_panel import EvidencePanelWidget
from desktop_app.videos.video_manager import VideoManager
from desktop_app.vector_store.vector_manager import VectorIndexJobState, VectorIndexStatus, VectorManager

logger = logging.getLogger(__name__)


class AccordionSection(QWidget):
    def __init__(self, title: str, content: QWidget, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.toggle_button = QToolButton()
        self.toggle_button.setText(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.toggle_button.setArrowType(Qt.ArrowType.RightArrow)
        self.toggle_button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.content = content
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.content)
        self.set_expanded(False)

    def set_expanded(self, expanded: bool) -> None:
        self.toggle_button.setChecked(expanded)
        self.toggle_button.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.content.setVisible(expanded)


class MainWindow(QMainWindow):
    def __init__(
        self,
        app_state: AppState,
        event_bus: EventBus,
        settings: QSettings | None = None,
        project_manager: ProjectManager | None = None,
        default_projects_dir: Path | None = None,
        settings_manager: SettingsManager | None = None,
        provider_manager: ProviderManager | None = None,
        video_manager: VideoManager | None = None,
        transcript_manager: TranscriptManager | None = None,
        transcript_repository: TranscriptRepository | None = None,
        knowledge_manager: KnowledgeManager | None = None,
        embedding_manager: EmbeddingManager | None = None,
        vector_manager: VectorManager | None = None,
        evidence_manager: EvidenceManager | None = None,
        compare_manager: CompareManager | None = None,
        bookmark_manager: BookmarkManager | None = None,
        highlight_manager: HighlightManager | None = None,
        answer_manager: AnswerManager | None = None,
        chat_manager: ChatManager | None = None,
        chat_session_manager: ChatSessionManager | None = None,
        memory_monitor: MemoryMonitor | None = None,
        hardware_profile: HardwareProfile | None = None,
        provider_health_service: ProviderHealthService | None = None,
        provider_health_repository: ProviderHealthRepository | None = None,
        provider_benchmark_repository: ProviderBenchmarkRepository | None = None,
        provider_usage_repository: ProviderUsageRepository | None = None,
        diagnostics_service: DiagnosticsService | None = None,
        packaging_audit_service: PackagingAuditService | None = None,
        session_recovery_service: SessionRecoveryService | None = None,
        update_service: UpdateService | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.app_state = app_state
        self.event_bus = event_bus
        self.settings = settings or QSettings(AppConstants.ORGANIZATION_NAME, AppConstants.APPLICATION_NAME)
        self.project_manager = project_manager
        self.default_projects_dir = default_projects_dir or Path.home() / "Advanced Video QA Pro Projects"
        self.settings_manager = settings_manager
        self.provider_manager = provider_manager
        self.video_manager = video_manager
        self.transcript_manager = transcript_manager
        self.transcript_repository = transcript_repository
        self.knowledge_manager = knowledge_manager
        self.embedding_manager = embedding_manager
        self.vector_manager = vector_manager
        self.evidence_manager = evidence_manager
        self.compare_manager = compare_manager
        self.bookmark_manager = bookmark_manager
        self.highlight_manager = highlight_manager
        self.answer_manager = answer_manager
        self.chat_manager = chat_manager
        self.chat_session_manager = chat_session_manager
        self.memory_monitor = memory_monitor
        self.hardware_profile = hardware_profile
        self.provider_health_service = provider_health_service
        self.provider_health_repository = provider_health_repository
        self.provider_benchmark_repository = provider_benchmark_repository
        self.provider_usage_repository = provider_usage_repository
        self.diagnostics_service = diagnostics_service
        self.packaging_audit_service = packaging_audit_service
        self.session_recovery_service = session_recovery_service
        self.update_service = update_service
        self.last_provider_health_results: list[ProviderHealthResult] = []
        self.last_diagnostics_snapshot: DiagnosticsSnapshot | None = None
        self.active_transcript_id: str | None = None
        self.active_chat_session_id: str | None = None
        self.last_answer_evidence_by_chunk: dict[str, EvidenceItem] = {}
        self.last_selected_evidence_item: EvidenceItem | None = None
        self._restoring_workspace_layout = False

        self.backend_status_label = QLabel()
        self.project_status_label = QLabel()
        self.message_label = QLabel()

        self.left_region: QWidget
        self.project_switcher: ProjectSwitcher
        self.video_library_widget: VideoLibraryWidget
        self.transcript_queue_widget: TranscriptQueueWidget
        self.center_region: VideoPlayer
        self.right_region: QWidget
        self.provider_selector: ProviderSelector
        self.memory_dashboard_widget: MemoryDashboardWidget | None = None
        self.provider_dashboard_widget: ProviderDashboardWidget
        self.diagnostics_panel_widget: DiagnosticsPanelWidget
        self.empty_project_hint: QLabel
        self.ai_workspace_tabs: QTabWidget
        self.plus_tab: QWidget
        self.workspace_tab_widgets: dict[str, QWidget]
        self.workspace_tab_titles: dict[str, str]
        self.workspace_widget_keys: dict[QWidget, str]
        self._last_workspace_tab_index = 0
        self.left_accordion_sections: list[AccordionSection]
        self.chat_workspace_widget: ChatWorkspaceWidget
        self.compare_workspace_widget: CompareWorkspaceWidget
        self.bookmark_panel_widget: BookmarkPanelWidget
        self.highlight_panel_widget: HighlightPanelWidget
        self.knowledge_summary_widget: KnowledgeSummaryWidget
        self.embedding_panel_widget: EmbeddingPanelWidget
        self.vector_index_panel_widget: VectorIndexPanelWidget
        self.evidence_panel_widget: EvidencePanelWidget
        self.bottom_region: TranscriptViewerWidget
        self.main_splitter: QSplitter
        self.work_splitter: QSplitter
        self.top_splitter: QSplitter
        self._visible_video_count = 0

        self.setWindowTitle(AppConstants.PRODUCT_NAME)
        self.setMinimumSize(AppConstants.MIN_WINDOW_WIDTH, AppConstants.MIN_WINDOW_HEIGHT)
        self.resize(AppConstants.DEFAULT_WINDOW_WIDTH, AppConstants.DEFAULT_WINDOW_HEIGHT)

        self.build_menu_bar()
        self.build_status_bar()
        self.build_layout()
        self.connect_events()
        self.restore_window_settings()
        self.update_backend_status(self.app_state.backend)
        self.update_project_status()

    def build_menu_bar(self) -> None:
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")
        new_project_action = QAction("New Project", self)
        new_project_action.setEnabled(self.project_manager is not None)
        new_project_action.triggered.connect(self.create_project)
        open_project_action = QAction("Open Project", self)
        open_project_action.setEnabled(self.project_manager is not None)
        open_project_action.triggered.connect(self.open_project_dialog)
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(new_project_action)
        file_menu.addAction(open_project_action)
        file_menu.addSeparator()
        file_menu.addAction(exit_action)

        view_menu = menu_bar.addMenu("&View")
        self.left_region_action = QAction("Toggle Left Panel", self, checkable=True)
        self.left_region_action.setChecked(True)
        self.left_region_action.triggered.connect(lambda checked: self.set_left_panel_visible(checked))
        self.right_region_action = QAction("Toggle Right Panel", self, checkable=True)
        self.right_region_action.setChecked(True)
        self.right_region_action.triggered.connect(lambda checked: self.set_right_panel_visible(checked))
        self.bottom_region_action = QAction("Toggle Bottom Panel", self, checkable=True)
        self.bottom_region_action.setChecked(True)
        self.bottom_region_action.triggered.connect(lambda checked: self.set_bottom_panel_visible(checked))
        reset_layout_action = QAction("Reset Workspace Layout", self)
        reset_layout_action.triggered.connect(lambda _: self.reset_workspace_layout())
        view_menu.addAction(self.left_region_action)
        view_menu.addAction(self.right_region_action)
        view_menu.addAction(self.bottom_region_action)
        view_menu.addSeparator()
        view_menu.addAction(reset_layout_action)
        view_menu.addSeparator()

        theme_menu = view_menu.addMenu("Theme")
        dark_action = QAction("Dark", self)
        light_action = QAction("Light", self)
        system_action = QAction("System", self)
        dark_action.triggered.connect(lambda: self.app_state.set_theme_mode(ThemeMode.DARK))
        light_action.triggered.connect(lambda: self.app_state.set_theme_mode(ThemeMode.LIGHT))
        system_action.triggered.connect(lambda: self.app_state.set_theme_mode(ThemeMode.SYSTEM))
        theme_menu.addAction(dark_action)
        theme_menu.addAction(light_action)
        theme_menu.addAction(system_action)

        tools_menu = menu_bar.addMenu("&Tools")
        settings_action = QAction("Settings", self)
        settings_action.setEnabled(self.settings_manager is not None)
        settings_action.triggered.connect(self.open_settings_dialog)
        provider_action = QAction("Provider Management", self)
        provider_action.setEnabled(self.provider_manager is not None)
        provider_action.triggered.connect(self.open_provider_management_dialog)
        diagnostics_action = QAction("Diagnostics", self)
        diagnostics_action.setEnabled(True)
        diagnostics_action.triggered.connect(self.open_diagnostics_panel)
        tools_menu.addAction(settings_action)
        tools_menu.addAction(provider_action)
        tools_menu.addAction(diagnostics_action)

        help_menu = menu_bar.addMenu("&Help")
        update_action = QAction("Check for Updates", self)
        update_action.setEnabled(self.update_service is not None)
        update_action.triggered.connect(self.check_for_updates)
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(update_action)
        help_menu.addAction(about_action)

    def build_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

        self.message_label.setText("Ready")
        status_bar.addWidget(self.message_label, 1)
        status_bar.addPermanentWidget(self.backend_status_label)
        status_bar.addPermanentWidget(self.project_status_label)

    def build_layout(self) -> None:
        self.left_region = QWidget()
        self.left_region.region_name = "left"  # type: ignore[attr-defined]
        self.left_region.setMinimumWidth(0)
        self.left_region.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.project_switcher = ProjectSwitcher()
        self.project_switcher.setMinimumWidth(0)
        self.project_switcher.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.project_switcher.setEnabled(self.project_manager is not None)
        self.project_switcher.create_requested.connect(self.create_project)
        self.project_switcher.open_requested.connect(self.open_project_dialog)
        self.project_switcher.project_selected.connect(self.open_project)
        self.project_switcher.archive_requested.connect(self.archive_project)
        self.project_switcher.restore_requested.connect(self.restore_project)
        self.project_switcher.delete_requested.connect(self.delete_project)

        self.video_library_widget = VideoLibraryWidget()
        self.video_library_widget.setMinimumWidth(0)
        self.video_library_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.video_library_widget.set_library_enabled(self.video_manager is not None)
        self.video_library_widget.import_requested.connect(self.import_videos)
        self.video_library_widget.open_requested.connect(self.open_video_from_library)
        self.video_library_widget.remove_requested.connect(self.remove_video)
        self.video_library_widget.refresh_requested.connect(self.refresh_video_library)
        self.video_library_widget.search_changed.connect(lambda _: self.refresh_video_library())
        self.transcript_queue_widget = TranscriptQueueWidget()
        self.transcript_queue_widget.setMinimumWidth(0)
        self.transcript_queue_widget.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.transcript_queue_widget.set_transcript_enabled(self.transcript_manager is not None)
        self.transcript_queue_widget.generate_requested.connect(self.generate_transcript_for_selected_video)
        self.transcript_queue_widget.cancel_requested.connect(self.cancel_transcript_job)
        self.transcript_queue_widget.retry_requested.connect(self.retry_transcript_job)
        transcript_hint = QLabel("Transcript text and timestamp navigation appear in the bottom workspace.")
        transcript_hint.setWordWrap(True)
        transcript_hint.setMargin(8)
        self.left_accordion_sections = [
            AccordionSection("Projects", self.project_switcher),
            AccordionSection("Videos", self.video_library_widget),
            AccordionSection("Transcript", transcript_hint),
            AccordionSection("Queue", self.transcript_queue_widget),
        ]
        for section in self.left_accordion_sections:
            section.toggle_button.clicked.connect(
                lambda checked=False, selected=section: self.set_left_accordion_section(selected, checked)
            )
        accordion_controls = QHBoxLayout()
        accordion_controls.setContentsMargins(0, 0, 0, 0)
        accordion_controls.setSpacing(4)
        self.expand_all_left_sections_button = QToolButton()
        self.expand_all_left_sections_button.setText("Expand All")
        self.expand_all_left_sections_button.clicked.connect(self.expand_all_left_accordion_sections)
        self.collapse_all_left_sections_button = QToolButton()
        self.collapse_all_left_sections_button.setText("Collapse All")
        self.collapse_all_left_sections_button.clicked.connect(self.collapse_all_left_accordion_sections)
        accordion_controls.addWidget(self.expand_all_left_sections_button)
        accordion_controls.addWidget(self.collapse_all_left_sections_button)

        left_layout = QVBoxLayout(self.left_region)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(2)
        left_layout.addLayout(accordion_controls)
        for section in self.left_accordion_sections:
            left_layout.addWidget(section)
        left_layout.addStretch(1)

        self.center_region = VideoPlayer()
        self.center_region.setMinimumWidth(0)
        self.center_region.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.center_region.snapshot_requested.connect(self.export_video_snapshot)
        self.center_region.error_changed.connect(lambda message: QMessageBox.warning(self, "Playback Error", message))
        self.center_region.playback.player.positionChanged.connect(self.sync_transcript_to_playback)
        self.right_region = QWidget()
        self.right_region.region_name = "right"  # type: ignore[attr-defined]
        self.right_region.setMinimumWidth(0)
        self.right_region.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Expanding)
        self.provider_selector = ProviderSelector(self.provider_manager)
        self.provider_selector.provider_selected.connect(self.handle_provider_selected)
        if self.memory_monitor is not None and self.hardware_profile is not None:
            self.memory_dashboard_widget = MemoryDashboardWidget(self.memory_monitor, self.hardware_profile)
        self.ai_workspace_tabs = QTabWidget()
        self.ai_workspace_tabs.setMinimumWidth(0)
        self.ai_workspace_tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.ai_workspace_tabs.setUsesScrollButtons(True)
        self.ai_workspace_tabs.tabBar().setExpanding(False)
        self.ai_workspace_tabs.setElideMode(Qt.TextElideMode.ElideRight)
        self.ai_workspace_tabs.setTabsClosable(True)
        self.ai_workspace_tabs.setMovable(True)
        self.ai_workspace_tabs.currentChanged.connect(self.handle_workspace_tab_changed)
        self.ai_workspace_tabs.tabCloseRequested.connect(self.close_workspace_tab)
        self.ai_workspace_tabs.tabBar().tabMoved.connect(lambda *_: self.keep_plus_tab_last())
        self.workspace_tab_widgets = {}
        self.workspace_tab_titles = {}
        self.workspace_widget_keys = {}
        self.empty_project_hint = QLabel(
            "<b>Welcome to Advanced Video QA Pro</b><br>"
            "1. Create or open a research project<br>"
            "2. Import a video<br>"
            "3. Generate a transcript<br>"
            "4. Generate knowledge, then ask questions"
        )
        self.empty_project_hint.setWordWrap(True)
        self.empty_project_hint.setMargin(10)
        self.chat_workspace_widget = ChatWorkspaceWidget()
        self.chat_workspace_widget.setMinimumHeight(420)
        self.chat_workspace_widget.question_requested.connect(self.generate_grounded_answer_for_active_project)
        self.chat_workspace_widget.new_chat_requested.connect(self.create_chat_session)
        self.chat_workspace_widget.session_selected.connect(self.open_chat_session)
        self.chat_workspace_widget.rename_chat_requested.connect(self.rename_chat_session)
        self.chat_workspace_widget.delete_chat_requested.connect(self.delete_chat_session)
        self.chat_workspace_widget.restore_previous_requested.connect(self.restore_previous_chat_session)
        self.chat_workspace_widget.search_requested.connect(self.search_chat_sessions)
        self.chat_workspace_widget.citation_selected.connect(self.handle_chat_citation_selected)
        self.compare_workspace_widget = CompareWorkspaceWidget()
        self.compare_workspace_widget.compare_requested.connect(self.compare_active_project_videos)
        self.compare_workspace_widget.evidence_selected.connect(self.handle_evidence_selected)
        self.bookmark_panel_widget = BookmarkPanelWidget()
        self.bookmark_panel_widget.bookmark_evidence_requested.connect(self.bookmark_current_evidence)
        self.bookmark_panel_widget.bookmark_segment_requested.connect(self.bookmark_current_transcript_segment)
        self.bookmark_panel_widget.bookmark_timestamp_requested.connect(self.bookmark_current_video_timestamp)
        self.bookmark_panel_widget.delete_requested.connect(self.delete_bookmark)
        self.bookmark_panel_widget.bookmark_selected.connect(self.handle_bookmark_selected)
        self.highlight_panel_widget = HighlightPanelWidget()
        self.highlight_panel_widget.highlight_transcript_requested.connect(self.highlight_current_transcript_segment)
        self.highlight_panel_widget.highlight_evidence_requested.connect(self.highlight_current_evidence)
        self.highlight_panel_widget.delete_requested.connect(self.delete_highlight)
        self.highlight_panel_widget.highlight_selected.connect(self.handle_highlight_selected)
        self.provider_dashboard_widget = ProviderDashboardWidget()
        self.provider_dashboard_widget.refresh_requested.connect(self.refresh_provider_health)
        self.diagnostics_panel_widget = DiagnosticsPanelWidget()
        self.diagnostics_panel_widget.refresh_requested.connect(self.refresh_diagnostics)
        self.diagnostics_panel_widget.export_requested.connect(self.export_diagnostics_report)
        self.knowledge_summary_widget = KnowledgeSummaryWidget()
        self.knowledge_summary_widget.generate_requested.connect(self.generate_knowledge_for_active_transcript)
        self.knowledge_summary_widget.chunk_selected.connect(self.seek_video_to_transcript_segment)
        self.embedding_panel_widget = EmbeddingPanelWidget()
        self.embedding_panel_widget.generate_requested.connect(self.generate_embeddings_for_active_transcript)
        self.embedding_panel_widget.cancel_requested.connect(self.cancel_embedding_job)
        self.embedding_panel_widget.retry_requested.connect(self.retry_embeddings_for_active_transcript)
        self.vector_index_panel_widget = VectorIndexPanelWidget()
        self.vector_index_panel_widget.build_requested.connect(self.build_vector_index_for_active_project)
        self.evidence_panel_widget = EvidencePanelWidget()
        self.evidence_panel_widget.search_requested.connect(self.generate_evidence_for_active_project)
        self.evidence_panel_widget.evidence_selected.connect(self.handle_evidence_selected)

        knowledge_tab = QWidget()
        knowledge_layout = QVBoxLayout(knowledge_tab)
        knowledge_layout.setContentsMargins(0, 0, 0, 0)
        knowledge_layout.setSpacing(0)
        knowledge_layout.addWidget(self.knowledge_summary_widget, 1)
        knowledge_layout.addWidget(self.embedding_panel_widget)

        providers_tab = QWidget()
        providers_layout = QVBoxLayout(providers_tab)
        providers_layout.setContentsMargins(0, 0, 0, 0)
        providers_layout.setSpacing(0)
        providers_layout.addWidget(self.provider_selector)
        providers_layout.addWidget(self.provider_dashboard_widget, 1)

        diagnostics_tab = QWidget()
        diagnostics_layout = QVBoxLayout(diagnostics_tab)
        diagnostics_layout.setContentsMargins(0, 0, 0, 0)
        diagnostics_layout.setSpacing(0)
        if self.memory_dashboard_widget is not None:
            diagnostics_layout.addWidget(self.memory_dashboard_widget)
        diagnostics_layout.addWidget(self.diagnostics_panel_widget, 1)
        diagnostics_layout.addWidget(self.vector_index_panel_widget)

        self.register_workspace_tab("chat", "Chat", self.chat_workspace_widget)
        self.register_workspace_tab("compare", "Compare", self.compare_workspace_widget)
        self.register_workspace_tab("knowledge", "Knowledge", knowledge_tab)
        self.register_workspace_tab("evidence", "Evidence", self.evidence_panel_widget)
        self.register_workspace_tab("bookmarks", "Bookmarks", self.bookmark_panel_widget)
        self.register_workspace_tab("highlights", "Highlights", self.highlight_panel_widget)
        self.register_workspace_tab("providers", "Providers", providers_tab)
        self.register_workspace_tab("diagnostics", "Diagnostics", diagnostics_tab)
        self.open_workspace_tab("chat")
        self.plus_tab = QWidget()
        self.ai_workspace_tabs.addTab(self.plus_tab, "+")
        self.ai_workspace_tabs.tabBar().setTabButton(
            self.ai_workspace_tabs.indexOf(self.plus_tab),
            self.ai_workspace_tabs.tabBar().ButtonPosition.RightSide,
            None,
        )
        right_layout = QVBoxLayout(self.right_region)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)
        right_layout.addWidget(self.empty_project_hint)
        right_layout.addWidget(self.ai_workspace_tabs, 1)
        self.bottom_region = TranscriptViewerWidget()
        self.bottom_region.setMinimumHeight(0)
        self.bottom_region.segment_selected.connect(self.seek_video_to_transcript_segment)
        self.bottom_region.export_requested.connect(self.export_transcript)

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(True)
        self.main_splitter.setOpaqueResize(False)

        self.work_splitter = QSplitter(Qt.Orientation.Vertical)
        self.work_splitter.setChildrenCollapsible(True)
        self.work_splitter.setOpaqueResize(False)

        self.top_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.top_splitter.setChildrenCollapsible(True)
        self.top_splitter.setOpaqueResize(False)
        self.top_splitter.addWidget(self.center_region)
        self.top_splitter.addWidget(self.right_region)

        self.work_splitter.addWidget(self.top_splitter)
        self.work_splitter.addWidget(self.bottom_region)

        self.main_splitter.addWidget(self.left_region)
        self.main_splitter.addWidget(self.work_splitter)
        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        self.top_splitter.setStretchFactor(0, 1)
        self.top_splitter.setStretchFactor(1, 0)
        self.work_splitter.setStretchFactor(0, 1)
        self.work_splitter.setStretchFactor(1, 0)
        self.main_splitter.splitterMoved.connect(lambda *_: self.handle_splitter_moved())
        self.work_splitter.splitterMoved.connect(lambda *_: self.handle_splitter_moved())
        self.top_splitter.splitterMoved.connect(lambda *_: self.handle_splitter_moved())
        self.reset_workspace_layout(save=False)

        self.setCentralWidget(self.main_splitter)
        self.refresh_project_switcher()
        self.refresh_video_library()
        self.refresh_compare_videos()
        self.refresh_bookmarks()
        self.refresh_highlights()

    def connect_events(self) -> None:
        self.event_bus.theme_changed.connect(self.handle_theme_changed)
        self.event_bus.backend_status_changed.connect(self.update_backend_status)
        self.event_bus.state_changed.connect(lambda _: self.update_project_status())
        self.event_bus.state_changed.connect(lambda _: self.refresh_project_switcher())
        self.event_bus.state_changed.connect(lambda _: self.refresh_video_library())
        self.event_bus.state_changed.connect(lambda _: self.refresh_chat_sessions())
        self.event_bus.state_changed.connect(lambda _: self.refresh_compare_videos())
        self.event_bus.state_changed.connect(lambda _: self.refresh_bookmarks())
        self.event_bus.state_changed.connect(lambda _: self.refresh_highlights())
        if self.video_manager is not None:
            self.video_manager.import_started.connect(lambda _: self.set_status_message("Importing video library item..."))
            self.video_manager.import_finished.connect(self.handle_video_import_finished)
            self.video_manager.import_failed.connect(self.handle_video_import_failed)
        if self.transcript_manager is not None:
            self.transcript_manager.job_queued.connect(self.handle_transcript_job_update)
            self.transcript_manager.progress_changed.connect(self.handle_transcript_job_update)
            self.transcript_manager.job_finished.connect(self.handle_transcript_job_update)
            self.transcript_manager.job_failed.connect(self.handle_transcript_job_update)
        if self.knowledge_manager is not None:
            self.knowledge_manager.structuring_started.connect(lambda _: self.set_status_message("Knowledge structuring started"))
            self.knowledge_manager.structuring_finished.connect(self.handle_knowledge_finished)
            self.knowledge_manager.structuring_failed.connect(self.handle_knowledge_failed)
        if self.embedding_manager is not None:
            self.embedding_manager.job_queued.connect(self.handle_embedding_job_update)
            self.embedding_manager.progress_changed.connect(self.handle_embedding_job_update)
            self.embedding_manager.job_finished.connect(self.handle_embedding_job_update)
            self.embedding_manager.job_failed.connect(self.handle_embedding_job_update)
        if self.vector_manager is not None:
            self.vector_manager.job_queued.connect(self.handle_vector_job_update)
            self.vector_manager.progress_changed.connect(self.handle_vector_job_update)
            self.vector_manager.job_finished.connect(self.handle_vector_job_update)
            self.vector_manager.job_failed.connect(self.handle_vector_job_update)
        if self.evidence_manager is not None:
            self.evidence_manager.job_queued.connect(self.handle_evidence_job_update)
            self.evidence_manager.progress_changed.connect(self.handle_evidence_job_update)
            self.evidence_manager.job_finished.connect(self.handle_evidence_finished)
            self.evidence_manager.job_failed.connect(self.handle_evidence_job_update)
        if self.answer_manager is not None:
            self.answer_manager.job_queued.connect(self.handle_answer_job_update)
            self.answer_manager.progress_changed.connect(self.handle_answer_job_update)
            self.answer_manager.job_finished.connect(self.handle_answer_finished)
            self.answer_manager.job_failed.connect(self.handle_answer_job_update)
        if self.chat_manager is not None:
            self.chat_manager.job_queued.connect(self.handle_chat_job_update)
            self.chat_manager.progress_changed.connect(self.handle_chat_job_update)
            self.chat_manager.message_finished.connect(self.handle_chat_message_finished)
            self.chat_manager.job_failed.connect(self.handle_chat_job_update)
        if self.compare_manager is not None:
            self.compare_manager.job_queued.connect(self.handle_compare_job_update)
            self.compare_manager.progress_changed.connect(self.handle_compare_job_update)
            self.compare_manager.job_finished.connect(self.handle_compare_finished)
            self.compare_manager.job_failed.connect(self.handle_compare_job_update)
        if self.bookmark_manager is not None:
            self.bookmark_manager.bookmarks_changed.connect(lambda _: self.refresh_bookmarks())
        if self.highlight_manager is not None:
            self.highlight_manager.highlights_changed.connect(lambda _: self.refresh_highlights())

    def register_workspace_tab(self, key: str, title: str, widget: QWidget) -> None:
        self.workspace_tab_widgets[key] = widget
        self.workspace_tab_titles[key] = title
        self.workspace_widget_keys[widget] = key

    def open_workspace_tab(self, key: str) -> None:
        widget = self.workspace_tab_widgets[key]
        existing_index = self.ai_workspace_tabs.indexOf(widget)
        if existing_index >= 0:
            self.ai_workspace_tabs.setCurrentIndex(existing_index)
            return
        insert_index = self._plus_tab_index()
        if insert_index < 0:
            insert_index = self.ai_workspace_tabs.count()
        new_index = self.ai_workspace_tabs.insertTab(insert_index, widget, self.workspace_tab_titles[key])
        self.ai_workspace_tabs.setCurrentIndex(new_index)
        self.keep_plus_tab_last()

    def close_workspace_tab(self, index: int) -> None:
        if index < 0 or index == self._plus_tab_index():
            return
        widget = self.ai_workspace_tabs.widget(index)
        self.ai_workspace_tabs.removeTab(index)
        if widget is not None:
            widget.setParent(None)
        if self.ai_workspace_tabs.count() == 1 and self._plus_tab_index() == 0:
            self.open_workspace_tab("chat")

    def handle_workspace_tab_changed(self, index: int) -> None:
        if index < 0:
            return
        if index == self._plus_tab_index():
            self.ai_workspace_tabs.setCurrentIndex(max(0, self._last_workspace_tab_index))
            self.show_workspace_tab_menu()
            return
        self._last_workspace_tab_index = index

    def show_workspace_tab_menu(self) -> None:
        menu = QMenu(self)
        for key, title in self.workspace_tab_titles.items():
            if self.ai_workspace_tabs.indexOf(self.workspace_tab_widgets[key]) < 0:
                action = menu.addAction(title)
                action.triggered.connect(lambda checked=False, selected=key: self.open_workspace_tab(selected))
        if menu.isEmpty():
            return
        tab_bar = self.ai_workspace_tabs.tabBar()
        plus_index = self._plus_tab_index()
        position = tab_bar.mapToGlobal(tab_bar.tabRect(max(0, plus_index)).bottomLeft())
        menu.exec(position)

    def keep_plus_tab_last(self) -> None:
        plus_index = self._plus_tab_index()
        last_index = self.ai_workspace_tabs.count() - 1
        if plus_index >= 0 and plus_index != last_index:
            self.ai_workspace_tabs.tabBar().moveTab(plus_index, last_index)
        plus_index = self._plus_tab_index()
        if plus_index >= 0:
            self.ai_workspace_tabs.tabBar().setTabButton(
                plus_index,
                self.ai_workspace_tabs.tabBar().ButtonPosition.RightSide,
                None,
            )

    def _plus_tab_index(self) -> int:
        plus_tab = getattr(self, "plus_tab", None)
        if not isinstance(plus_tab, QWidget):
            return -1
        return self.ai_workspace_tabs.indexOf(plus_tab)

    def set_left_accordion_section(self, selected_section: AccordionSection, expanded: bool = True) -> None:
        selected_section.set_expanded(expanded)

    def expand_all_left_accordion_sections(self) -> None:
        for section in self.left_accordion_sections:
            section.set_expanded(True)

    def collapse_all_left_accordion_sections(self) -> None:
        for section in self.left_accordion_sections:
            section.set_expanded(False)

    def restore_window_settings(self) -> None:
        geometry = self.settings.value(AppConstants.SETTINGS_KEY_GEOMETRY)
        if geometry:
            self.restoreGeometry(geometry)
        window_state = self.settings.value(AppConstants.SETTINGS_KEY_STATE)
        if window_state:
            self.restoreState(window_state)
        self.restore_workspace_layout()

    def save_window_settings(self) -> None:
        self.settings.setValue(AppConstants.SETTINGS_KEY_GEOMETRY, self.saveGeometry())
        self.settings.setValue(AppConstants.SETTINGS_KEY_STATE, self.saveState())
        self.save_workspace_layout()
        self.settings.sync()

    def restore_workspace_layout(self) -> None:
        left_width = self._settings_int(AppConstants.SETTINGS_KEY_LEFT_WIDTH, AppConstants.LEFT_REGION_WIDTH)
        right_width = self._settings_int(AppConstants.SETTINGS_KEY_RIGHT_WIDTH, AppConstants.RIGHT_REGION_WIDTH)
        bottom_height = self._settings_int(AppConstants.SETTINGS_KEY_BOTTOM_HEIGHT, AppConstants.BOTTOM_REGION_HEIGHT)
        self.apply_workspace_layout(left_width=left_width, right_width=right_width, bottom_height=bottom_height)

    def save_workspace_layout(self) -> None:
        left_width = self.main_splitter.sizes()[0] if self.main_splitter.count() > 0 else 0
        right_width = self.top_splitter.sizes()[1] if self.top_splitter.count() > 1 else 0
        bottom_height = self.work_splitter.sizes()[1] if self.work_splitter.count() > 1 else 0
        self.settings.setValue(AppConstants.SETTINGS_KEY_LEFT_WIDTH, left_width)
        self.settings.setValue(AppConstants.SETTINGS_KEY_RIGHT_WIDTH, right_width)
        self.settings.setValue(AppConstants.SETTINGS_KEY_BOTTOM_HEIGHT, bottom_height)

    def apply_workspace_layout(self, *, left_width: int, right_width: int, bottom_height: int) -> None:
        self._restoring_workspace_layout = True
        try:
            total_width = max(sum(self.main_splitter.sizes()), self.main_splitter.width(), AppConstants.MIN_WINDOW_WIDTH)
            left_width, work_width = self._clamped_split_pair(left_width, total_width - left_width, total_width)
            self.main_splitter.setSizes([left_width, work_width])

            top_total_width = max(sum(self.top_splitter.sizes()), self.top_splitter.width(), work_width)
            center_width, right_width = self._clamped_split_pair(
                top_total_width - right_width,
                right_width,
                top_total_width,
            )
            self.top_splitter.setSizes([center_width, right_width])

            total_height = max(sum(self.work_splitter.sizes()), self.work_splitter.height(), AppConstants.MIN_WINDOW_HEIGHT)
            top_height, bottom_height = self._clamped_split_pair(
                total_height - bottom_height,
                bottom_height,
                total_height,
            )
            self.work_splitter.setSizes([top_height, bottom_height])
            self.update_panel_actions()
        finally:
            self._restoring_workspace_layout = False

    def reset_workspace_layout(self, *, save: bool = True) -> None:
        self.apply_workspace_layout(
            left_width=AppConstants.LEFT_REGION_WIDTH,
            right_width=AppConstants.RIGHT_REGION_WIDTH,
            bottom_height=AppConstants.BOTTOM_REGION_HEIGHT,
        )
        if save:
            self.save_workspace_layout()
            self.settings.sync()
            self.set_status_message("Workspace layout reset")

    def set_left_panel_visible(self, visible: bool) -> None:
        current = self.main_splitter.sizes()
        work_width = max(200, sum(current) - (AppConstants.LEFT_REGION_WIDTH if visible else 0))
        self.main_splitter.setSizes([AppConstants.LEFT_REGION_WIDTH if visible else 0, work_width])
        self.update_panel_actions()
        self.save_workspace_layout()

    def set_right_panel_visible(self, visible: bool) -> None:
        current = self.top_splitter.sizes()
        center_width = max(200, sum(current) - (AppConstants.RIGHT_REGION_WIDTH if visible else 0))
        self.top_splitter.setSizes([center_width, AppConstants.RIGHT_REGION_WIDTH if visible else 0])
        self.update_panel_actions()
        self.save_workspace_layout()

    def set_bottom_panel_visible(self, visible: bool) -> None:
        current = self.work_splitter.sizes()
        top_height = max(200, sum(current) - (AppConstants.BOTTOM_REGION_HEIGHT if visible else 0))
        self.work_splitter.setSizes([top_height, AppConstants.BOTTOM_REGION_HEIGHT if visible else 0])
        self.update_panel_actions()
        self.save_workspace_layout()

    def update_panel_actions(self) -> None:
        self.left_region_action.blockSignals(True)
        self.right_region_action.blockSignals(True)
        self.bottom_region_action.blockSignals(True)
        self.left_region_action.setChecked(self.main_splitter.sizes()[0] > 0)
        self.right_region_action.setChecked(self.top_splitter.sizes()[1] > 0)
        self.bottom_region_action.setChecked(self.work_splitter.sizes()[1] > 0)
        self.left_region_action.blockSignals(False)
        self.right_region_action.blockSignals(False)
        self.bottom_region_action.blockSignals(False)

    def handle_splitter_moved(self) -> None:
        if not self._restoring_workspace_layout:
            self.update_panel_actions()

    def _clamped_split_pair(self, first: int, second: int, total: int) -> tuple[int, int]:
        total = max(1, int(total))
        first = max(0, int(first))
        second = max(0, int(second))
        if first == 0:
            return 0, total
        if second == 0:
            first = min(first, total)
            return first, total - first
        min_primary = min(200, total)
        max_first = max(min_primary, total - 1)
        first = min(max(first, min_primary), max_first)
        second = max(1, total - first)
        return first, second

    def _settings_int(self, key: str, default: int) -> int:
        value = self.settings.value(key, default)
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def set_status_message(self, message: str) -> None:
        self.message_label.setText(message)

    def handle_theme_changed(self, theme_state: ThemeState) -> None:
        self.set_status_message(f"Theme: {theme_state.mode.value.title()}")

    def update_backend_status(self, backend_state: BackendState) -> None:
        status = backend_state.status.value.title()
        if backend_state.status == BackendStatus.ERROR and backend_state.error_message:
            status = f"Backend: Error"
        else:
            status = f"Backend: {status}"
        self.backend_status_label.setText(status)

    def update_project_status(self) -> None:
        self.project_status_label.setText(f"Project: {self.app_state.project.active_project_name}")
        self.update_empty_project_guidance()

    def refresh_project_switcher(self) -> None:
        if self.project_manager is None:
            self.project_switcher.set_projects([], None)
            return
        projects = self.project_manager.project_service.list_projects(include_archived=True)
        self.project_switcher.set_projects(projects, self.app_state.project.active_project_id)

    def refresh_provider_selector(self) -> None:
        self.provider_selector.refresh()

    def restore_recovery_snapshot(self) -> None:
        if self.session_recovery_service is None:
            return
        payload = self.session_recovery_service.load_snapshot()
        if not payload:
            return
        project_id = str(payload.get("project_id") or "")
        if project_id and self.project_manager is not None:
            try:
                self.project_manager.open_project(project_id)
            except Exception:
                logger.warning("Could not restore recovered project %s", project_id, exc_info=True)
        layout = payload.get("layout")
        if isinstance(layout, dict):
            self.apply_workspace_layout(
                left_width=int(layout.get("left_width") or AppConstants.LEFT_REGION_WIDTH),
                right_width=int(layout.get("right_width") or AppConstants.RIGHT_REGION_WIDTH),
                bottom_height=int(layout.get("bottom_height") or AppConstants.BOTTOM_REGION_HEIGHT),
            )
        video_path = Path(str(payload.get("video_path") or ""))
        if video_path.exists():
            self.center_region.open_video(video_path, project_workspace=self.app_state.project.workspace_path)
            position_ms = int(payload.get("video_position_ms") or 0)
            if position_ms:
                self.center_region.playback.seek(position_ms)
        self.active_chat_session_id = str(payload.get("chat_session_id") or "") or None
        self.set_status_message("Recovered previous desktop session")

    def refresh_provider_health(self) -> None:
        if self.provider_health_service is None:
            self.provider_dashboard_widget.set_results([])
            return
        self.set_status_message("Checking provider health...")
        results = self.provider_health_service.check_all(include_env=True)
        self.last_provider_health_results = results
        usage_summary = None
        if self.provider_usage_repository is not None and self.app_state.project.active_project_id:
            usage_summary = self.provider_usage_repository.summarize(self.app_state.project.active_project_id)
        self.provider_dashboard_widget.set_results(
            results,
            usage_summary=usage_summary,
            benchmark_repository=self.provider_benchmark_repository,
        )
        responded = [result.provider.value for result in results if result.responded]
        self.set_status_message(
            f"Provider health checked: {', '.join(responded) if responded else 'no providers responded'}"
        )

    def refresh_diagnostics(self) -> None:
        if self.diagnostics_service is None:
            return
        worker_status = "Warm worker pool active" if self.memory_monitor is not None else "Desktop workers unavailable"
        queue_status = "Task queues managed by desktop TaskRunner"
        snapshot = self.diagnostics_service.capture(
            provider_results=self.last_provider_health_results,
            worker_status=worker_status,
            queue_status=queue_status,
        )
        self.last_diagnostics_snapshot = snapshot
        self.diagnostics_panel_widget.set_snapshot(snapshot)
        self.set_status_message("Diagnostics refreshed")

    def export_diagnostics_report(self) -> None:
        if self.diagnostics_service is None:
            return
        if self.last_diagnostics_snapshot is None:
            self.refresh_diagnostics()
        if self.last_diagnostics_snapshot is None:
            return
        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Diagnostics Report",
            str(Path.home() / "advanced_video_qa_diagnostics.json"),
            "JSON (*.json)",
        )
        if not output_path:
            return
        exported = self.diagnostics_service.export_report(self.last_diagnostics_snapshot, Path(output_path))
        self.set_status_message(f"Diagnostics exported: {exported.name}")

    def refresh_video_library(self) -> None:
        active_project_id = self.app_state.project.active_project_id
        enabled = self.video_manager is not None and active_project_id is not None
        self.video_library_widget.set_library_enabled(enabled)
        self.refresh_vector_status()
        if not enabled or self.video_manager is None or active_project_id is None:
            self._visible_video_count = 0
            self.video_library_widget.set_videos([])
            self.compare_workspace_widget.set_videos([])
            self.transcript_queue_widget.set_transcript_enabled(False)
            self.evidence_panel_widget.clear()
            self.update_empty_project_guidance()
            return
        search = self.video_library_widget.search_input.text()
        videos = self.video_manager.list_project_videos(active_project_id, search=search)
        self._visible_video_count = len(videos)
        self.video_library_widget.set_videos(videos)
        self.compare_workspace_widget.set_videos(self.video_manager.list_project_videos(active_project_id))
        self.transcript_queue_widget.set_transcript_enabled(self.transcript_manager is not None)
        self.update_empty_project_guidance()

    def update_empty_project_guidance(self) -> None:
        no_active_project = self.app_state.project.active_project_id is None
        show_guidance = no_active_project or self._visible_video_count == 0
        if no_active_project:
            text = (
                "<b>Welcome to Advanced Video QA Pro</b><br>"
                "1. Create or open a research project<br>"
                "2. Import a video<br>"
                "3. Generate a transcript<br>"
                "4. Generate knowledge, then ask questions"
            )
        else:
            text = (
                "<b>Project is ready</b><br>"
                "1. Import a video from the left panel<br>"
                "2. Generate a transcript<br>"
                "3. Generate knowledge<br>"
                "4. Ask questions in Chat"
            )
        self.empty_project_hint.setText(text)
        self.empty_project_hint.setVisible(show_guidance)

    def refresh_compare_videos(self) -> None:
        active_project_id = self.app_state.project.active_project_id
        if self.video_manager is None or active_project_id is None:
            self.compare_workspace_widget.set_videos([])
            return
        self.compare_workspace_widget.set_videos(self.video_manager.list_project_videos(active_project_id))

    def refresh_bookmarks(self) -> None:
        project_id = self.app_state.project.active_project_id
        if self.bookmark_manager is None or project_id is None:
            self.bookmark_panel_widget.set_bookmarks([])
            return
        self.bookmark_panel_widget.set_bookmarks(self.bookmark_manager.list_project_bookmarks(project_id))

    def refresh_highlights(self) -> None:
        project_id = self.app_state.project.active_project_id
        if self.highlight_manager is None or project_id is None:
            self.highlight_panel_widget.set_highlights([])
            return
        self.highlight_panel_widget.set_highlights(self.highlight_manager.list_project_highlights(project_id))

    def import_videos(self) -> None:
        if self.video_manager is None:
            return
        active_project_id = self.app_state.project.active_project_id
        if active_project_id is None:
            QMessageBox.information(self, "No Project", "Open or create a project before importing videos.")
            return
        start_dir = self.app_state.project.workspace_path or str(Path.home())
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Import Videos",
            start_dir,
            "Videos (*.mp4 *.mkv *.avi *.mov *.webm)",
        )
        if not files:
            return
        self.video_manager.import_videos_async(active_project_id, files)

    def remove_video(self, video_id: str) -> None:
        if self.video_manager is None:
            return
        answer = QMessageBox.question(
            self,
            "Remove Video",
            "Remove this video from the library? Project files are not deleted.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.video_manager.remove_video(video_id):
            self.set_status_message("Video removed")
            self.refresh_video_library()

    def open_video_from_library(self, video_id: str) -> None:
        if self.video_manager is None:
            return
        video = self.video_manager.get_video(video_id)
        if video is None:
            QMessageBox.warning(self, "Open Video Failed", "Video was not found in the library.")
            return
        self.center_region.open_video(video.file_path, project_workspace=self.app_state.project.workspace_path)
        self.load_latest_transcript_for_video(video.id)
        self.set_status_message(f"Opened video: {video.name}")

    def export_video_snapshot(self) -> None:
        try:
            snapshot_path = self.center_region.export_snapshot()
        except SnapshotError as exc:
            QMessageBox.warning(self, "Snapshot Failed", str(exc))
            return
        self.set_status_message(f"Snapshot exported: {snapshot_path.name}")

    def generate_transcript_for_selected_video(self, model_name: str) -> None:
        if self.transcript_manager is None:
            return
        video_id = self.video_library_widget.selected_video_id()
        if not video_id:
            QMessageBox.information(self, "No Video Selected", "Select a video before generating a transcript.")
            return
        self.transcript_manager.start_transcription(video_id, model_name=model_name)
        self.set_status_message("Transcript queued")

    def cancel_transcript_job(self, job_id: str) -> None:
        if self.transcript_manager is None:
            return
        self.transcript_manager.cancel(job_id)
        self.set_status_message("Transcript cancellation requested")

    def retry_transcript_job(self, video_id: str, model_name: str) -> None:
        if self.transcript_manager is None:
            return
        self.transcript_manager.retry(video_id, model_name=model_name)
        self.set_status_message("Transcript retry queued")

    def handle_transcript_job_update(self, state: TranscriptJobState) -> None:
        self.transcript_queue_widget.add_or_update_job(state)
        if state.status == TranscriptStatus.COMPLETED and self.video_library_widget.selected_video_id() == state.video_id:
            self.load_latest_transcript_for_video(state.video_id)
        self.set_status_message(f"Transcript: {state.status.value} ({state.progress_percent}%)")

    def load_latest_transcript_for_video(self, video_id: str) -> None:
        if self.transcript_repository is None:
            self.bottom_region.clear()
            self.active_transcript_id = None
            self.knowledge_summary_widget.clear()
            self.embedding_panel_widget.reset_for_transcript()
            return
        transcripts = [
            transcript
            for transcript in self.transcript_repository.list_by_video(video_id)
            if transcript.status == TranscriptStatus.COMPLETED
        ]
        if not transcripts:
            self.bottom_region.clear()
            self.active_transcript_id = None
            self.knowledge_summary_widget.clear()
            self.embedding_panel_widget.reset_for_transcript()
            return
        transcript = transcripts[0]
        segments = self.transcript_repository.list_segments(transcript.id)
        self.bottom_region.load_transcript(transcript, segments)
        self.active_transcript_id = transcript.id
        self.refresh_knowledge_summary(transcript.id)
        self.refresh_embedding_status(transcript.id)

    def seek_video_to_transcript_segment(self, position_ms: int) -> None:
        self.center_region.playback.seek(position_ms)

    def sync_transcript_to_playback(self, position_ms: int) -> None:
        self.bottom_region.set_playback_position(position_ms)

    def export_transcript(self, format_name: str) -> None:
        workspace_path = self.app_state.project.workspace_path
        if not workspace_path:
            QMessageBox.warning(self, "Export Failed", "Open a project before exporting transcripts.")
            return
        try:
            export_path = self.bottom_region.export_current(format_name, Path(workspace_path) / "Exports")
        except Exception as exc:
            QMessageBox.warning(self, "Export Failed", str(exc))
            return
        self.set_status_message(f"Transcript exported: {export_path.name}")

    def generate_knowledge_for_active_transcript(self) -> None:
        if self.knowledge_manager is None or self.active_transcript_id is None:
            QMessageBox.information(self, "No Transcript", "Open a completed transcript before generating knowledge chunks.")
            return
        self.knowledge_manager.structure_transcript_async(self.active_transcript_id)

    def refresh_knowledge_summary(self, transcript_id: str) -> None:
        if self.knowledge_manager is None:
            self.knowledge_summary_widget.clear()
            return
        self.knowledge_summary_widget.set_chunks(self.knowledge_manager.list_chunks(transcript_id))

    def handle_knowledge_finished(self, task_id: str, result: object) -> None:
        _ = task_id
        chunks = result if isinstance(result, list) else []
        self.open_workspace_tab("knowledge")
        self.knowledge_summary_widget.set_chunks(chunks)
        self.set_status_message(f"Knowledge chunks generated: {len(chunks)}")

    def handle_knowledge_failed(self, task_id: str, error: object) -> None:
        _ = task_id
        QMessageBox.warning(self, "Knowledge Structuring Failed", str(error))
        self.set_status_message("Knowledge structuring failed")

    def refresh_embedding_status(self, transcript_id: str) -> None:
        if self.embedding_manager is None:
            self.embedding_panel_widget.reset_for_transcript()
            return
        count = self.embedding_manager.count_for_transcript(
            transcript_id,
            self.embedding_panel_widget.selected_model(),
        )
        self.embedding_panel_widget.reset_for_transcript(count)

    def refresh_vector_status(self) -> None:
        project_id = self.app_state.project.active_project_id
        workspace_path = self.app_state.project.workspace_path
        if self.vector_manager is None or self.settings_manager is None or project_id is None or not workspace_path:
            self.vector_index_panel_widget.reset_for_project()
            return
        try:
            record = self.vector_manager.latest_index(project_id, self.settings_manager.current.embedding_selection)
        except Exception:
            record = None
        self.vector_index_panel_widget.reset_for_project(record.index_path if record else "")

    def generate_embeddings_for_active_transcript(self, model_name: str) -> None:
        if self.embedding_manager is None or self.active_transcript_id is None:
            QMessageBox.information(self, "No Transcript", "Open a completed transcript with knowledge chunks before generating embeddings.")
            return
        if self.settings_manager is not None and self.settings_manager.current.low_memory_mode:
            model_name = "BAAI/bge-small-en-v1.5"
        self.embedding_manager.generate_embeddings_async(self.active_transcript_id, model_name)
        self.set_status_message("Embedding generation queued")

    def cancel_embedding_job(self, job_id: str) -> None:
        if self.embedding_manager is None:
            return
        self.embedding_manager.cancel(job_id)
        self.set_status_message("Embedding cancellation requested")

    def retry_embeddings_for_active_transcript(self, model_name: str) -> None:
        if self.embedding_manager is None or self.active_transcript_id is None:
            return
        self.embedding_manager.retry(self.active_transcript_id, model_name)
        self.set_status_message("Embedding retry queued")

    def handle_embedding_job_update(self, state: EmbeddingJobState) -> None:
        self.embedding_panel_widget.apply_state(state)
        if state.status == EmbeddingStatus.COMPLETED:
            self.open_workspace_tab("knowledge")
            self.set_status_message(f"Embeddings generated: {state.record_count}")
        elif state.status == EmbeddingStatus.FAILED:
            self.set_status_message("Embedding generation failed")
        else:
            self.set_status_message(f"Embeddings: {state.status.value} ({state.progress_percent}%)")

    def build_vector_index_for_active_project(self) -> None:
        if self.vector_manager is None or self.settings_manager is None:
            return
        project_id = self.app_state.project.active_project_id
        workspace_path = self.app_state.project.workspace_path
        if project_id is None or not workspace_path:
            QMessageBox.information(self, "No Project", "Open a project before building a FAISS index.")
            return
        self.vector_manager.build_index_async(
            project_id=project_id,
            project_workspace=Path(workspace_path),
            embedding_selection=self.settings_manager.current.embedding_selection,
        )
        self.set_status_message("FAISS index build queued")

    def handle_vector_job_update(self, state: VectorIndexJobState) -> None:
        self.vector_index_panel_widget.apply_state(state)
        if state.status == VectorIndexStatus.COMPLETED:
            self.open_workspace_tab("diagnostics")
            self.set_status_message(f"FAISS index built: {state.vector_count} vectors")
        elif state.status == VectorIndexStatus.FAILED:
            self.set_status_message("FAISS index build failed")
        else:
            self.set_status_message(f"FAISS index: {state.status.value} ({state.progress_percent}%)")

    def generate_evidence_for_active_project(self, query: str, top_k: int, min_similarity: float) -> None:
        if self.evidence_manager is None or self.settings_manager is None:
            return
        project_id = self.app_state.project.active_project_id
        if project_id is None:
            QMessageBox.information(self, "No Project", "Open a project before searching evidence.")
            return
        self.evidence_manager.generate_async(
            project_id=project_id,
            query=query,
            embedding_selection=self.settings_manager.current.embedding_selection,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        self.set_status_message("Evidence search queued")

    def handle_evidence_finished(self, result: object) -> None:
        if isinstance(result, EvidenceResult):
            self.open_workspace_tab("evidence")
            self.evidence_panel_widget.set_result(result)
            self.set_status_message(f"Evidence candidates: {len(result.items)}")
            return
        if isinstance(result, EvidenceJobState):
            self.handle_evidence_job_update(result)

    def handle_evidence_job_update(self, state: EvidenceJobState) -> None:
        self.evidence_panel_widget.apply_state(state)
        if state.status == EvidenceStatus.FAILED:
            self.set_status_message("Evidence search failed")
        else:
            self.set_status_message(f"Evidence: {state.status.value} ({state.progress_percent}%)")

    def handle_evidence_selected(self, item: object) -> None:
        if not isinstance(item, EvidenceItem):
            return
        self.last_selected_evidence_item = item
        if self.video_manager is not None:
            self.center_region.open_video(
                Path(item.source.file_path),
                project_workspace=self.app_state.project.workspace_path,
            )
            self.load_latest_transcript_for_video(item.source.video_id)
        self.seek_video_to_transcript_segment(item.start_ms)
        self.bottom_region.set_playback_position(item.start_ms)
        self.set_status_message(f"Evidence selected: {item.source.video_name} @ {item.start_time:.1f}s")

    def bookmark_current_evidence(self, title: str, note: str) -> None:
        if self.bookmark_manager is None:
            return
        item = self.last_selected_evidence_item
        if item is None:
            QMessageBox.information(self, "No Evidence", "Select an evidence item before bookmarking evidence.")
            return
        self.bookmark_manager.bookmark_evidence(item, title=title or item.topic_title, note=note)
        self.refresh_bookmarks()
        self.set_status_message("Evidence bookmarked")

    def bookmark_current_transcript_segment(self, title: str, note: str) -> None:
        if self.bookmark_manager is None:
            return
        active = self._active_transcript_segment()
        if active is None or self.bottom_region.transcript is None:
            QMessageBox.information(self, "No Transcript Segment", "Select or play to a transcript segment first.")
            return
        project_id = self.app_state.project.active_project_id
        if project_id is None:
            return
        self.bookmark_manager.bookmark_transcript_segment(
            project_id=project_id,
            video_id=self.bottom_region.transcript.video_id,
            transcript_id=self.bottom_region.transcript.id,
            segment=active,
            title=title or f"Transcript @ {active.start_time:.1f}s",
            note=note,
        )
        self.refresh_bookmarks()
        self.set_status_message("Transcript segment bookmarked")

    def bookmark_current_video_timestamp(self, title: str, note: str) -> None:
        if self.bookmark_manager is None:
            return
        project_id = self.app_state.project.active_project_id
        video_id = self._active_video_id()
        if project_id is None or video_id is None:
            QMessageBox.information(self, "No Video", "Open or select a video before bookmarking a timestamp.")
            return
        timestamp = self.center_region.playback.player.position() / 1000.0
        self.bookmark_manager.bookmark_video_timestamp(
            project_id=project_id,
            video_id=video_id,
            timestamp=timestamp,
            title=title or f"Video @ {timestamp:.1f}s",
            note=note,
        )
        self.refresh_bookmarks()
        self.set_status_message("Video timestamp bookmarked")

    def delete_bookmark(self, bookmark_id: str) -> None:
        if self.bookmark_manager is None:
            return
        if self.bookmark_manager.delete_bookmark(bookmark_id):
            self.refresh_bookmarks()
            self.set_status_message("Bookmark deleted")

    def handle_bookmark_selected(self, bookmark: object) -> None:
        if isinstance(bookmark, Bookmark):
            self._jump_to_video_marker(bookmark.video_id, bookmark.timestamp)
            self.set_status_message(f"Bookmark selected: {bookmark.title}")

    def highlight_current_transcript_segment(self, color_name: str, selected_text: str, note: str) -> None:
        if self.highlight_manager is None:
            return
        active = self._active_transcript_segment()
        if active is None or self.bottom_region.transcript is None:
            QMessageBox.information(self, "No Transcript Segment", "Select or play to a transcript segment first.")
            return
        project_id = self.app_state.project.active_project_id
        if project_id is None:
            return
        self.highlight_manager.highlight_transcript_segment(
            project_id=project_id,
            video_id=self.bottom_region.transcript.video_id,
            transcript_id=self.bottom_region.transcript.id,
            segment=active,
            color=HighlightColor(color_name),
            note=note,
            selected_text=selected_text,
        )
        self.refresh_highlights()
        self.set_status_message("Transcript highlighted")

    def highlight_current_evidence(self, color_name: str, note: str) -> None:
        if self.highlight_manager is None:
            return
        item = self.last_selected_evidence_item
        if item is None:
            QMessageBox.information(self, "No Evidence", "Select an evidence item before highlighting evidence.")
            return
        self.highlight_manager.highlight_evidence(item, color=HighlightColor(color_name), note=note)
        self.refresh_highlights()
        self.set_status_message("Evidence highlighted")

    def delete_highlight(self, highlight_id: str) -> None:
        if self.highlight_manager is None:
            return
        if self.highlight_manager.delete_highlight(highlight_id):
            self.refresh_highlights()
            self.set_status_message("Highlight deleted")

    def handle_highlight_selected(self, highlight: object) -> None:
        if isinstance(highlight, Highlight):
            self._jump_to_video_marker(highlight.video_id, highlight.timestamp)
            self.set_status_message(f"Highlight selected: {highlight.color.value} @ {highlight.timestamp:.1f}s")

    def _active_video_id(self) -> str | None:
        if self.bottom_region.transcript is not None:
            return self.bottom_region.transcript.video_id
        return self.video_library_widget.selected_video_id()

    def _active_transcript_segment(self):
        if not self.bottom_region.segments:
            return None
        active_index = self.bottom_region.model.active_index
        if active_index is None:
            current = self.bottom_region.segment_view.currentIndex()
            active_index = current.row() if current.isValid() else None
        if active_index is None or not 0 <= active_index < len(self.bottom_region.segments):
            return None
        return self.bottom_region.segments[active_index]

    def _jump_to_video_marker(self, video_id: str, timestamp: float) -> None:
        if self.video_manager is not None and video_id:
            video = self.video_manager.get_video(video_id)
            if video is not None:
                self.center_region.open_video(
                    Path(video.file_path),
                    project_workspace=self.app_state.project.workspace_path,
                )
                self.load_latest_transcript_for_video(video.id)
        position_ms = int(max(0.0, timestamp) * 1000)
        self.seek_video_to_transcript_segment(position_ms)
        self.bottom_region.set_playback_position(position_ms)

    def compare_active_project_videos(
        self,
        session_name: str,
        video_ids: list[str],
        query: str,
        min_similarity: float,
    ) -> None:
        if self.compare_manager is None or self.settings_manager is None:
            return
        project_id = self.app_state.project.active_project_id
        if project_id is None:
            QMessageBox.information(self, "No Project", "Open a project before comparing videos.")
            return
        if not 2 <= len(video_ids) <= 10:
            QMessageBox.information(self, "Compare Videos", "Select between 2 and 10 videos.")
            return
        self.compare_manager.compare_async(
            project_id=project_id,
            session_name=session_name,
            video_ids=video_ids,
            query=query,
            embedding_selection=self.settings_manager.current.embedding_selection,
            min_similarity=min_similarity,
        )
        self.set_status_message("Multi-video comparison queued")

    def handle_compare_finished(self, result: object) -> None:
        if isinstance(result, CompareResult):
            self.open_workspace_tab("compare")
            self.compare_workspace_widget.set_result(result)
            self.evidence_panel_widget.set_result(
                EvidenceResult(
                    project_id=result.project_id,
                    query=result.query,
                    duration_ms=result.duration_ms,
                    items=result.evidence_items,
                )
            )
            self.set_status_message(f"Compared {len(result.video_ids)} videos")
            return
        if isinstance(result, CompareJobState):
            self.handle_compare_job_update(result)

    def handle_compare_job_update(self, state: CompareJobState) -> None:
        self.compare_workspace_widget.apply_state(state)
        if state.status == CompareStatus.FAILED:
            self.set_status_message("Multi-video comparison failed")
        else:
            self.set_status_message(f"Compare: {state.status.value} ({state.progress_percent}%)")

    def refresh_chat_sessions(self) -> None:
        project_id = self.app_state.project.active_project_id
        if self.chat_session_manager is None or project_id is None:
            self.active_chat_session_id = None
            self.chat_workspace_widget.set_sessions([])
            self.chat_workspace_widget.set_messages([])
            return
        session = self.chat_session_manager.ensure_active_session(project_id)
        self.active_chat_session_id = session.id
        sessions = self.chat_session_manager.list_sessions(project_id)
        self.chat_workspace_widget.set_sessions(sessions, session.id)
        self.load_chat_messages(session.id)

    def load_chat_messages(self, session_id: str) -> None:
        if self.chat_session_manager is None:
            return
        messages = self.chat_session_manager.chat_repository.list_messages(session_id)
        self.chat_workspace_widget.set_messages(messages)

    def create_chat_session(self) -> None:
        project_id = self.app_state.project.active_project_id
        if self.chat_session_manager is None or project_id is None:
            QMessageBox.information(self, "No Project", "Open a project before creating a chat.")
            return
        session = self.chat_session_manager.create_session(project_id)
        self.active_chat_session_id = session.id
        self.refresh_chat_sessions()
        self.set_status_message("New chat created")

    def open_chat_session(self, session_id: str) -> None:
        if self.chat_session_manager is None:
            return
        session = self.chat_session_manager.set_active_session(session_id)
        if session is None:
            return
        self.active_chat_session_id = session.id
        self.load_chat_messages(session.id)
        self.set_status_message(f"Chat opened: {session.title}")

    def rename_chat_session(self, session_id: str, title: str) -> None:
        if self.chat_session_manager is None:
            return
        session = self.chat_session_manager.rename_session(session_id, title)
        if session is not None:
            self.refresh_chat_sessions()
            self.set_status_message(f"Chat renamed: {session.title}")

    def delete_chat_session(self, session_id: str) -> None:
        if self.chat_session_manager is None:
            return
        session = self.chat_session_manager.delete_session(session_id)
        if session is not None:
            self.active_chat_session_id = None
            self.refresh_chat_sessions()
            self.set_status_message("Chat deleted")

    def restore_previous_chat_session(self) -> None:
        project_id = self.app_state.project.active_project_id
        if self.chat_session_manager is None or project_id is None:
            return
        deleted = [
            session
            for session in self.chat_session_manager.list_sessions(project_id, include_deleted=True)
            if session.deleted_at is not None
        ]
        if not deleted:
            self.set_status_message("No deleted chat to restore")
            return
        session = self.chat_session_manager.restore_session(deleted[0].id)
        if session is not None:
            self.active_chat_session_id = session.id
            self.refresh_chat_sessions()
            self.set_status_message(f"Chat restored: {session.title}")

    def search_chat_sessions(self, query: str) -> None:
        project_id = self.app_state.project.active_project_id
        if self.chat_session_manager is None or project_id is None:
            return
        query = query.strip()
        if not query:
            self.refresh_chat_sessions()
            return
        results = self.chat_session_manager.search(project_id, query)
        self.open_workspace_tab("chat")
        self.chat_workspace_widget.set_search_results(results)
        self.set_status_message(f"Chat search matches: {len(results)}")

    def generate_grounded_answer_for_active_project(self, question: str, top_k: int, min_similarity: float) -> None:
        if self.chat_manager is None or self.chat_session_manager is None or self.settings_manager is None:
            return
        project_id = self.app_state.project.active_project_id
        if project_id is None:
            QMessageBox.information(self, "No Project", "Open a project before generating a grounded answer.")
            return
        session = self.chat_session_manager.ensure_active_session(project_id)
        self.active_chat_session_id = session.id
        self.open_workspace_tab("chat")
        self.chat_workspace_widget.set_sessions(self.chat_session_manager.list_sessions(project_id), session.id)
        self.chat_manager.ask_async(
            session_id=session.id,
            project_id=project_id,
            question=question,
            embedding_selection=self.settings_manager.current.embedding_selection,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        self.set_status_message("Chat answer queued")

    def handle_chat_message_finished(self, result: object) -> None:
        if not isinstance(result, ChatMessage):
            if isinstance(result, ChatJobState):
                self.handle_chat_job_update(result)
            return
        self.chat_workspace_widget.append_message(result)
        self.open_workspace_tab("chat")
        self.last_answer_evidence_by_chunk = {item.chunk_id: item for item in result.evidence_items}
        if result.evidence_items:
            self.evidence_panel_widget.set_result(
                EvidenceResult(
                    project_id=result.project_id,
                    query=result.question,
                    duration_ms=result.duration_ms,
                    items=result.evidence_items,
                )
            )
        if self.chat_session_manager is not None:
            self.refresh_chat_sessions()
        self.set_status_message(f"Chat answer generated via {result.provider}")

    def handle_chat_job_update(self, state: ChatJobState) -> None:
        self.chat_workspace_widget.apply_state(state)
        if state.status.value == "failed":
            message = state.error_message or "Internal exception: chat answer failed without an error message."
            self.chat_workspace_widget.set_error(message)
            self.set_status_message(message)
        else:
            self.set_status_message(f"Chat answer: {state.status.value} ({state.progress_percent}%)")

    def handle_chat_citation_selected(self, citation: object) -> None:
        if not isinstance(citation, Citation):
            return
        evidence_item = self.last_answer_evidence_by_chunk.get(citation.chunk_id)
        if evidence_item is not None:
            self.handle_evidence_selected(evidence_item)
            return
        if citation.source_file_path:
            self.center_region.open_video(
                Path(citation.source_file_path),
                project_workspace=self.app_state.project.workspace_path,
            )
            if citation.source_video_id:
                self.load_latest_transcript_for_video(citation.source_video_id)
        position_ms = int(citation.timestamp_start * 1000)
        self.seek_video_to_transcript_segment(position_ms)
        self.bottom_region.set_playback_position(position_ms)
        self.set_status_message(f"Citation selected: {citation.source_video} @ {citation.timestamp_start:.1f}s")

    def handle_answer_finished(self, result: object) -> None:
        if isinstance(result, AnswerResult):
            self.open_workspace_tab("chat")
            self.chat_workspace_widget.set_result(result)
            self.last_answer_evidence_by_chunk = {item.chunk_id: item for item in result.evidence_items}
            self.evidence_panel_widget.set_result(
                EvidenceResult(
                    project_id=result.project_id,
                    query=result.question,
                    duration_ms=result.duration_ms,
                    items=result.evidence_items,
                )
            )
            self.set_status_message(f"Grounded answer generated via {result.provider}")
            return
        if isinstance(result, AnswerJobState):
            self.handle_answer_job_update(result)

    def handle_answer_job_update(self, state: AnswerJobState) -> None:
        self.chat_workspace_widget.apply_state(state)
        if state.status == AnswerStatus.FAILED:
            message = state.error_message or "Internal exception: grounded answer failed without an error message."
            self.chat_workspace_widget.set_error(message)
            self.set_status_message(message)
        else:
            self.set_status_message(f"Grounded answer: {state.status.value} ({state.progress_percent}%)")

    def handle_video_import_finished(self, task_id: str, result: object) -> None:
        _ = task_id
        count = len(result) if isinstance(result, list) else 0
        self.set_status_message(f"Imported {count} video{'s' if count != 1 else ''}")
        self.refresh_video_library()

    def handle_video_import_failed(self, task_id: str, error: object) -> None:
        _ = task_id
        QMessageBox.warning(self, "Video Import Failed", str(error))
        self.set_status_message("Video import failed")
        self.refresh_video_library()

    def open_settings_dialog(self) -> None:
        if self.settings_manager is None:
            return
        dialog = SettingsDialog(self.settings_manager, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        self.app_state.set_theme_mode(self.settings_manager.current.theme)
        self.refresh_provider_selector()
        self.set_status_message("Settings saved")

    def open_provider_management_dialog(self) -> None:
        if self.provider_manager is None:
            return
        dialog = ProviderManagementDialog(self.provider_manager, self)
        dialog.exec()
        self.refresh_provider_selector()
        self.set_status_message("Provider profiles updated")

    def open_diagnostics_panel(self) -> None:
        self.open_workspace_tab("diagnostics")
        self.refresh_diagnostics()

    def check_for_updates(self) -> None:
        if self.update_service is None:
            return
        result = self.update_service.check_for_update()
        if not result.checked:
            QMessageBox.information(self, "Updates", result.message)
            return
        if result.update_available:
            notes = f"\n\nRelease notes:\n{result.release_notes[:1000]}" if result.release_notes else ""
            QMessageBox.information(
                self,
                "Update Available",
                f"{result.latest_version} is available.\n\nInstall manually from:\n{result.release_url}{notes}",
            )
        else:
            QMessageBox.information(self, "Updates", result.message)

    def handle_provider_selected(self, provider_id: str) -> None:
        if self.provider_manager is None:
            return
        profile = self.provider_manager.get_provider(provider_id)
        if profile:
            self.set_status_message(f"Provider: {profile.provider_name.value}")

    def create_project(self) -> None:
        if self.project_manager is None:
            return
        dialog = CreateProjectDialog(self.default_projects_dir, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        name, description, root_path = dialog.project_values()
        try:
            project = self.project_manager.create_project(
                name=name,
                description=description,
                root_path=root_path,
            )
        except Exception as exc:
            logger.exception("Could not create project")
            QMessageBox.warning(self, "Create Project Failed", str(exc))
            return
        self.set_status_message(f"Project created: {project.name}")

    def open_project_dialog(self) -> None:
        if self.project_manager is None:
            return
        projects = self.project_manager.project_service.list_projects(include_archived=True)
        if not projects:
            QMessageBox.information(self, "No Projects", "Create a project first.")
            return
        dialog = OpenProjectDialog(projects, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        project_id = dialog.selected_project_id()
        if project_id:
            self.open_project(project_id)

    def open_project(self, project_id: str) -> None:
        if self.project_manager is None:
            return
        try:
            project = self.project_manager.open_project(project_id)
        except Exception as exc:
            logger.exception("Could not open project")
            QMessageBox.warning(self, "Open Project Failed", str(exc))
            return
        self.set_status_message(f"Project opened: {project.name}")

    def archive_project(self, project_id: str) -> None:
        if self.project_manager is None:
            return
        project = self.project_manager.archive_project(project_id)
        if project:
            self.set_status_message(f"Project archived: {project.name}")

    def restore_project(self, project_id: str) -> None:
        if self.project_manager is None:
            return
        project = self.project_manager.restore_project(project_id)
        if project:
            self.set_status_message(f"Project restored: {project.name}")
            self.refresh_project_switcher()

    def delete_project(self, project_id: str) -> None:
        if self.project_manager is None:
            return
        answer = QMessageBox.question(
            self,
            "Delete Project",
            "Delete this project from the app database? Project files are not removed.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        if self.project_manager.delete_project(project_id):
            self.set_status_message("Project deleted")
            self.refresh_project_switcher()

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            AppConstants.PRODUCT_NAME,
            f"{AppConstants.PRODUCT_NAME}\nVersion {AppConstants.APPLICATION_VERSION}\n\nSprint 18 bookmarks, highlights, and memory audit.",
        )

    def save_recovery_snapshot(self) -> None:
        if self.session_recovery_service is None:
            return
        layout = {
            "left_width": self.main_splitter.sizes()[0] if self.main_splitter.count() > 0 else 0,
            "right_width": self.top_splitter.sizes()[1] if self.top_splitter.count() > 1 else 0,
            "bottom_height": self.work_splitter.sizes()[1] if self.work_splitter.count() > 1 else 0,
        }
        snapshot = self.session_recovery_service.create_snapshot(
            project_id=self.app_state.project.active_project_id or "",
            project_name=self.app_state.project.active_project_name,
            workspace_path=self.app_state.project.workspace_path or "",
            chat_session_id=self.active_chat_session_id or "",
            compare_session_id="",
            video_path=str(self.center_region.current_video_path or ""),
            video_position_ms=int(self.center_region.playback.player.position()),
            layout=layout,
        )
        self.session_recovery_service.save_snapshot(snapshot)

    def closeEvent(self, event: QCloseEvent) -> None:
        logger.info("Main window closing")
        self.event_bus.app_closing.emit()
        self.save_recovery_snapshot()
        self.save_window_settings()
        event.accept()
