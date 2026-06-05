from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSettings

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.core.events import EventBus
from desktop_app.evidence.evidence_models import EvidenceItem, EvidenceSource
from desktop_app.evidence.evidence_repository import EvidenceRepository
from desktop_app.evidence.evidence_service import EvidenceService
from desktop_app.knowledge.knowledge_models import ChunkTopic, KnowledgeChunk
from desktop_app.knowledge.knowledge_repository import KnowledgeRepository
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.retrieval.retrieval_models import RetrievalChunk, RetrievalHit, RetrievalResult
from desktop_app.main_window import MainWindow
from desktop_app.state.app_state import AppState
from desktop_app.transcripts.transcript_models import Transcript, TranscriptSegment, TranscriptStatus
from desktop_app.transcripts.transcript_repository import TranscriptRepository
from desktop_app.videos.video_metadata import VideoMetadata
from desktop_app.videos.video_model import VideoRecord
from desktop_app.videos.video_repository import VideoRepository
from desktop_app.widgets.evidence_panel import EvidencePanelWidget


class FakeRetrievalService:
    def __init__(self, hits: list[RetrievalHit]) -> None:
        self.hits = hits

    def search(self, *, project_id, query, embedding_selection, top_k=5, min_similarity=0.0):
        return RetrievalResult(
            project_id=project_id,
            query=query,
            embedding_model="BAAI/bge-small-en-v1.5",
            top_k=top_k,
            duration_ms=12.0,
            hits=self.hits[:top_k],
        )


def _setup_evidence_chunks(tmp_path: Path):
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Evidence Project",
        root_path=str(tmp_path / "project"),
    )
    video_path = tmp_path / "lecture.mp4"
    video_path.write_bytes(b"video")
    video = VideoRepository(database.connection).save(
        VideoRecord.create(
            project_id=project.id,
            name=video_path.name,
            file_path=str(video_path),
            file_size=video_path.stat().st_size,
            metadata=VideoMetadata(duration=60.0, fps=30.0, width=1280, height=720),
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
    transcript_repository.replace_segments(
        transcript.id,
        [
            TranscriptSegment.create(
                transcript_id=transcript.id,
                start_time=0,
                end_time=20,
                text="Machine learning basics.",
                confidence=0.9,
            )
        ],
    )
    chunks = [
        KnowledgeChunk.create(
            transcript_id=transcript.id,
            start_time=0,
            end_time=20,
            chunk_text="Machine learning basics introduce supervised and unsupervised learning.",
            topic_title="Machine Learning Basics",
            confidence=0.95,
        ),
        KnowledgeChunk.create(
            transcript_id=transcript.id,
            start_time=20,
            end_time=40,
            chunk_text="Dimensionality reduction compresses a large data set.",
            topic_title="Dimensionality Reduction",
            confidence=0.9,
        ),
    ]
    KnowledgeRepository(database.connection).replace_chunks(
        transcript.id,
        chunks,
        [
            ChunkTopic.create(chunk_id=chunk.chunk_id, topic_title=chunk.topic_title, confidence=chunk.confidence)
            for chunk in chunks
        ],
    )
    return database, project, video, chunks


def _hit(chunk: KnowledgeChunk, rank: int, similarity: float, confidence: float) -> RetrievalHit:
    return RetrievalHit(
        chunk=RetrievalChunk(
            chunk_id=chunk.chunk_id,
            transcript_id=chunk.transcript_id,
            start_time=chunk.start_time,
            end_time=chunk.end_time,
            chunk_text=chunk.chunk_text,
            topic_title=chunk.topic_title,
            confidence=chunk.confidence,
            word_count=chunk.word_count,
        ),
        rank=rank,
        raw_score=similarity,
        similarity_score=similarity,
        confidence_score=confidence,
        topic_score=0.0,
    )


def test_evidence_service_generates_source_backed_items_and_history(tmp_path) -> None:
    database, project, video, chunks = _setup_evidence_chunks(tmp_path)
    service = EvidenceService(
        EvidenceRepository(database.connection),
        FakeRetrievalService(
            [
                _hit(chunks[1], 2, 0.82, 0.74),
                _hit(chunks[0], 1, 0.91, 0.86),
            ]
        ),
    )

    result = service.generate(
        project_id=project.id,
        query="machine learning",
        embedding_selection="small",
        top_k=2,
    )
    history = EvidenceRepository(database.connection).list_history(project.id)

    assert len(result.items) == 2
    assert result.items[0].source.video_id == video.id
    assert result.items[0].source.video_name == video.name
    assert result.items[0].confidence_score >= result.items[1].confidence_score
    assert len(history) == 2


def test_evidence_panel_virtualizes_and_paginates_large_lists(qapp, tmp_path) -> None:
    database, project, _video, chunks = _setup_evidence_chunks(tmp_path)
    service = EvidenceService(
        EvidenceRepository(database.connection),
        FakeRetrievalService([_hit(chunks[0], 1, 0.9, 0.8)]),
    )
    item = service.generate(project_id=project.id, query="machine learning", embedding_selection="small").items[0]
    widget = EvidencePanelWidget()

    widget.model.set_items([item] * 10_001)

    assert widget.model.rowCount() == 100
    assert widget.model.page_count() == 101
    widget.model.set_page(100)
    assert widget.model.rowCount() == 1


def test_evidence_panel_click_emits_selected_item(qapp, tmp_path) -> None:
    database, project, _video, chunks = _setup_evidence_chunks(tmp_path)
    service = EvidenceService(
        EvidenceRepository(database.connection),
        FakeRetrievalService([_hit(chunks[0], 1, 0.9, 0.8)]),
    )
    item = service.generate(project_id=project.id, query="machine learning", embedding_selection="small").items[0]
    widget = EvidencePanelWidget()
    emitted = []
    widget.evidence_selected.connect(emitted.append)

    widget.model.set_items([item])
    widget._emit_evidence_selected(widget.model.index(0))

    assert emitted == [item]


def test_evidence_selection_seeks_video_and_highlights_transcript(qapp, tmp_path) -> None:
    settings = QSettings(str(tmp_path / "window.ini"), QSettings.Format.IniFormat)
    event_bus = EventBus()
    state = AppState(event_bus)
    window = MainWindow(state, event_bus, settings)
    transcript = Transcript.create(
        video_id="video-1",
        model_name="tiny",
        language="en",
        status=TranscriptStatus.COMPLETED,
    )
    segments = [
        TranscriptSegment.create(
            transcript_id=transcript.id,
            start_time=10.0,
            end_time=20.0,
            text="Evidence segment",
            confidence=0.9,
        )
    ]
    window.bottom_region.load_transcript(transcript, segments)

    class FakePlayback:
        def __init__(self) -> None:
            self.position_ms = 0

        def seek(self, position_ms: int) -> None:
            self.position_ms = position_ms

    fake_playback = FakePlayback()
    window.center_region.playback = fake_playback
    item = EvidenceItem.create(
        project_id="project",
        query="evidence",
        chunk_id="chunk",
        retrieval_rank=1,
        source=EvidenceSource(
            video_id="video-1",
            video_name="lecture.mp4",
            file_path=str(tmp_path / "lecture.mp4"),
            transcript_id=transcript.id,
        ),
        topic_title="Evidence Topic",
        start_time=10.0,
        end_time=20.0,
        similarity_score=0.9,
        confidence_score=0.8,
        chunk_text="Evidence segment",
    )

    window.handle_evidence_selected(item)

    assert fake_playback.position_ms == 10_000
    assert window.bottom_region.model.active_index == 0
    window.close()
