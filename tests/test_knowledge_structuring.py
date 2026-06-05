from __future__ import annotations

import json
from pathlib import Path

import pytest

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.knowledge.chunking_engine import KnowledgeStructuringError, SemanticChunkingEngine
from desktop_app.knowledge.knowledge_models import KnowledgeChunk
from desktop_app.knowledge.knowledge_repository import KnowledgeRepository
from desktop_app.knowledge.knowledge_service import KnowledgeService
from desktop_app.knowledge.topic_extractor import TopicExtractor
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.transcripts.transcript_models import Transcript, TranscriptSegment, TranscriptStatus
from desktop_app.transcripts.transcript_repository import TranscriptRepository
from desktop_app.videos.video_metadata import VideoMetadata
from desktop_app.videos.video_model import VideoRecord
from desktop_app.videos.video_repository import VideoRepository
from desktop_app.widgets.knowledge_summary import KnowledgeSummaryWidget


def _setup_transcript(tmp_path, segments: list[TranscriptSegment] | None = None):
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project_service = ProjectService(ProjectRepository(database.connection))
    project = project_service.create_project(name="Knowledge Project", root_path=str(tmp_path / "project"))
    video_repository = VideoRepository(database.connection)
    video_path = tmp_path / "lecture.mp4"
    video_path.write_bytes(b"video")
    video = video_repository.save(
        VideoRecord.create(
            project_id=project.id,
            name=video_path.name,
            file_path=str(video_path),
            file_size=video_path.stat().st_size,
            metadata=VideoMetadata(duration=3600.0, fps=24.0, width=1280, height=720),
            thumbnail_path="",
        )
    )
    transcript_repository = TranscriptRepository(database.connection)
    transcript = Transcript.create(
        video_id=video.id,
        model_name="base",
        language="en",
        status=TranscriptStatus.COMPLETED,
    )
    transcript_repository.save_transcript(transcript)
    if segments is None:
        segments = _multi_topic_segments(transcript.id)
    transcript_repository.replace_segments(transcript.id, segments)
    return database, transcript, transcript_repository


def _multi_topic_segments(transcript_id: str) -> list[TranscriptSegment]:
    texts = [
        "In this video we introduce machine learning and explain what learning algorithms do.",
        "Machine learning basics include supervised learning, unsupervised learning, and practical examples.",
        "Now we discuss neural networks, hidden layers, activations, and deep learning model behavior.",
        "Neural network training uses loss values and gradients to improve model predictions.",
        "Next we cover model evaluation, validation sets, accuracy, precision, and recall.",
        "Practical advice helps teams apply machine learning systems successfully in real-world projects.",
    ]
    return [
        TranscriptSegment.create(
            transcript_id=transcript_id,
            start_time=float(index * 60),
            end_time=float(index * 60 + 55),
            text=text,
            confidence=0.9,
        )
        for index, text in enumerate(texts)
    ]


def test_semantic_chunking_detects_multi_topic_boundaries(tmp_path) -> None:
    _, transcript, transcript_repository = _setup_transcript(tmp_path)
    segments = transcript_repository.list_segments(transcript.id)
    engine = SemanticChunkingEngine(min_chunk_words=12, max_chunk_words=45)

    chunks = engine.chunk(segments)

    assert len(chunks) >= 2
    assert chunks[0].start_time == 0.0
    assert chunks[-1].end_time > chunks[0].end_time


def test_topic_extractor_generates_human_readable_titles() -> None:
    extractor = TopicExtractor()

    assert extractor.extract("This section introduces machine learning basics and supervised learning.").title == "Machine Learning Basics"
    assert extractor.extract("We evaluate accuracy, validation, precision and recall.").title == "Model Evaluation"


def test_knowledge_service_persists_chunks_and_topics(tmp_path) -> None:
    database, transcript, transcript_repository = _setup_transcript(tmp_path)
    knowledge_repository = KnowledgeRepository(database.connection)
    service = KnowledgeService(
        knowledge_repository,
        transcript_repository,
        chunking_engine=SemanticChunkingEngine(min_chunk_words=12, max_chunk_words=45),
    )

    chunks = service.structure_transcript(transcript.id)
    persisted = knowledge_repository.list_chunks(transcript.id)
    topics = knowledge_repository.list_topics(chunks[0].chunk_id)

    assert chunks
    assert len(persisted) == len(chunks)
    assert topics
    assert persisted[0].word_count > 0


def test_corrupted_transcript_without_text_fails(tmp_path) -> None:
    database, transcript, transcript_repository = _setup_transcript(tmp_path, [])
    bad_segment = TranscriptSegment.create(
        transcript_id=transcript.id,
        start_time=0,
        end_time=1,
        text="",
        confidence=0.0,
    )
    transcript_repository.replace_segments(transcript.id, [bad_segment])
    service = KnowledgeService(
        KnowledgeRepository(database.connection),
        transcript_repository,
        chunking_engine=SemanticChunkingEngine(min_chunk_words=5, max_chunk_words=30),
    )

    with pytest.raises(KnowledgeStructuringError):
        service.structure_transcript(transcript.id)


def test_large_one_hour_transcript_structures_without_fixed_size_split(tmp_path) -> None:
    database, transcript, transcript_repository = _setup_transcript(tmp_path, [])
    large_segments = [
        TranscriptSegment.create(
            transcript_id=transcript.id,
            start_time=float(index * 30),
            end_time=float(index * 30 + 25),
            text=(
                "Machine learning basics and learning algorithms appear in this lecture segment. "
                if index < 60
                else "Model evaluation validation accuracy and practical advice appear in this lecture segment. "
            )
            + f"Example number {index}.",
            confidence=0.86,
        )
        for index in range(120)
    ]
    transcript_repository.replace_segments(transcript.id, large_segments)
    service = KnowledgeService(
        KnowledgeRepository(database.connection),
        transcript_repository,
        chunking_engine=SemanticChunkingEngine(min_chunk_words=80, max_chunk_words=220),
    )

    chunks = service.structure_transcript(transcript.id)

    assert len(chunks) >= 2
    assert sum(chunk.word_count for chunk in chunks) >= 1200
    assert chunks[0].start_time == 0.0


def test_real_cached_video_chunks_can_be_structured(tmp_path) -> None:
    real_chunks_path = Path("data/chunks/01_index.json")
    if not real_chunks_path.exists():
        pytest.skip("Real cached chunks are not available.")
    payload = json.loads(real_chunks_path.read_text(encoding="utf-8"))
    database, transcript, transcript_repository = _setup_transcript(tmp_path, [])
    segments = [
        TranscriptSegment.create(
            transcript_id=transcript.id,
            start_time=float(chunk["start"]),
            end_time=float(chunk["end"]),
            text=str(chunk["text"]),
            confidence=1.0,
        )
        for chunk in payload.get("chunks", [])
    ]
    transcript_repository.replace_segments(transcript.id, segments)
    service = KnowledgeService(
        KnowledgeRepository(database.connection),
        transcript_repository,
        chunking_engine=SemanticChunkingEngine(min_chunk_words=50, max_chunk_words=320),
    )

    chunks = service.structure_transcript(transcript.id)

    assert chunks
    assert any("Machine Learning" in chunk.topic_title for chunk in chunks)


def test_knowledge_summary_click_emits_timestamp(qapp) -> None:
    widget = KnowledgeSummaryWidget()
    chunk = KnowledgeChunk.create(
        transcript_id="transcript",
        start_time=12.5,
        end_time=25.0,
        chunk_text="Machine learning basics",
        topic_title="Machine Learning Basics",
        confidence=0.9,
    )
    emitted: list[int] = []
    widget.chunk_selected.connect(emitted.append)

    widget.set_chunks([chunk])
    widget._emit_selected_chunk(widget.chunk_list.item(0))

    assert emitted == [12_500]
