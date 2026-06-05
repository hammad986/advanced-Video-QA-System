from __future__ import annotations

from desktop_app.bookmarks.bookmark_manager import BookmarkManager
from desktop_app.bookmarks.bookmark_models import BookmarkType
from desktop_app.bookmarks.bookmark_repository import BookmarkRepository
from desktop_app.bookmarks.bookmark_service import BookmarkService
from desktop_app.database.database_manager import DatabaseManager
from desktop_app.evidence.evidence_models import EvidenceItem, EvidenceSource
from desktop_app.highlights.highlight_manager import HighlightManager
from desktop_app.highlights.highlight_models import HighlightColor
from desktop_app.highlights.highlight_repository import HighlightRepository
from desktop_app.highlights.highlight_service import HighlightService
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.transcripts.transcript_models import TranscriptSegment
from desktop_app.widgets.bookmark_panel import BookmarkPanelWidget
from desktop_app.widgets.highlight_panel import HighlightPanelWidget


def test_bookmark_service_persists_evidence_segment_and_timestamp(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Marks Project",
        root_path=str(tmp_path / "project"),
    )
    repository = BookmarkRepository(database.connection)
    service = BookmarkService(repository)
    evidence = _evidence(project.id)
    segment = TranscriptSegment.create(
        transcript_id="transcript-1",
        start_time=12.0,
        end_time=15.0,
        text="Important transcript segment.",
    )

    evidence_bookmark = service.bookmark_evidence(evidence, title="Evidence", note="keep")
    segment_bookmark = service.bookmark_transcript_segment(
        project_id=project.id,
        video_id="video-1",
        transcript_id="transcript-1",
        segment=segment,
        title="Segment",
    )
    timestamp_bookmark = service.bookmark_video_timestamp(
        project_id=project.id,
        video_id="video-1",
        timestamp=42.5,
        title="Timestamp",
    )
    bookmarks = repository.list_by_project(project.id)

    assert evidence_bookmark.bookmark_type == BookmarkType.EVIDENCE
    assert segment_bookmark.segment_id == segment.id
    assert timestamp_bookmark.timestamp == 42.5
    assert len(bookmarks) == 3


def test_highlight_service_persists_transcript_and_evidence_highlights(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Highlights Project",
        root_path=str(tmp_path / "project"),
    )
    repository = HighlightRepository(database.connection)
    service = HighlightService(repository)
    segment = TranscriptSegment.create(
        transcript_id="transcript-1",
        start_time=20.0,
        end_time=25.0,
        text="Highlight this transcript segment.",
    )

    transcript_highlight = service.highlight_transcript_segment(
        project_id=project.id,
        video_id="video-1",
        transcript_id="transcript-1",
        segment=segment,
        color=HighlightColor.YELLOW,
        selected_text="Highlight this",
    )
    evidence_highlight = service.highlight_evidence(_evidence(project.id), color=HighlightColor.BLUE, note="evidence")
    highlights = repository.list_by_project(project.id)

    assert transcript_highlight.highlighted_text == "Highlight this"
    assert evidence_highlight.chunk_id == "chunk-1"
    assert {highlight.color for highlight in highlights} == {HighlightColor.YELLOW, HighlightColor.BLUE}


def test_bookmark_and_highlight_managers_emit_changes(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Manager Project",
        root_path=str(tmp_path / "project"),
    )
    bookmark_manager = BookmarkManager(BookmarkService(BookmarkRepository(database.connection)))
    highlight_manager = HighlightManager(HighlightService(HighlightRepository(database.connection)))
    bookmark_events = []
    highlight_events = []
    bookmark_manager.bookmarks_changed.connect(bookmark_events.append)
    highlight_manager.highlights_changed.connect(highlight_events.append)

    bookmark_manager.bookmark_evidence(_evidence(project.id), title="Evidence")
    highlight_manager.highlight_evidence(_evidence(project.id), color=HighlightColor.GREEN)

    assert bookmark_events == [project.id]
    assert highlight_events == [project.id]


def test_bookmark_and_highlight_panels_emit_actions(qapp) -> None:
    bookmark_panel = BookmarkPanelWidget()
    highlight_panel = HighlightPanelWidget()
    bookmark_events = []
    highlight_events = []
    bookmark_panel.bookmark_evidence_requested.connect(lambda title, note: bookmark_events.append(("evidence", title, note)))
    bookmark_panel.bookmark_segment_requested.connect(lambda title, note: bookmark_events.append(("segment", title, note)))
    bookmark_panel.bookmark_timestamp_requested.connect(lambda title, note: bookmark_events.append(("timestamp", title, note)))
    highlight_panel.highlight_transcript_requested.connect(
        lambda color, text, note: highlight_events.append(("transcript", color, text, note))
    )
    highlight_panel.highlight_evidence_requested.connect(lambda color, note: highlight_events.append(("evidence", color, note)))

    bookmark_panel.title_input.setText("Mark")
    bookmark_panel.note_input.setPlainText("Note")
    bookmark_panel.bookmark_evidence_button.click()
    bookmark_panel.bookmark_segment_button.click()
    bookmark_panel.bookmark_timestamp_button.click()
    highlight_panel.selected_text_input.setPlainText("Text")
    highlight_panel.note_input.setPlainText("Highlight note")
    highlight_panel.highlight_transcript_button.click()
    highlight_panel.highlight_evidence_button.click()

    assert bookmark_events == [
        ("evidence", "Mark", "Note"),
        ("segment", "Mark", "Note"),
        ("timestamp", "Mark", "Note"),
    ]
    assert highlight_events[0][0] == "transcript"
    assert highlight_events[0][2] == "Text"
    assert highlight_events[1][0] == "evidence"


def _evidence(project_id: str) -> EvidenceItem:
    return EvidenceItem.create(
        project_id=project_id,
        query="What matters?",
        chunk_id="chunk-1",
        retrieval_rank=1,
        source=EvidenceSource(
            video_id="video-1",
            video_name="lecture.mp4",
            file_path="D:/videos/lecture.mp4",
            transcript_id="transcript-1",
        ),
        topic_title="Important Topic",
        start_time=10.0,
        end_time=20.0,
        similarity_score=0.9,
        confidence_score=0.8,
        chunk_text="This evidence should be preserved.",
    )
