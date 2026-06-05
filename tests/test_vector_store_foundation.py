from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import psutil

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.embeddings.embedding_models import DEFAULT_EMBEDDING_MODELS, EmbeddingRecord
from desktop_app.embeddings.embedding_repository import EmbeddingRepository
from desktop_app.knowledge.knowledge_models import ChunkTopic, KnowledgeChunk
from desktop_app.knowledge.knowledge_repository import KnowledgeRepository
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.transcripts.transcript_models import Transcript, TranscriptSegment, TranscriptStatus
from desktop_app.transcripts.transcript_repository import TranscriptRepository
from desktop_app.vector_store.faiss_index import FaissIndexBuilder
from desktop_app.vector_store.vector_repository import VectorRepository
from desktop_app.vector_store.vector_service import EmbeddingModelSelector, VectorService
from desktop_app.videos.video_metadata import VideoMetadata
from desktop_app.videos.video_model import VideoRecord
from desktop_app.videos.video_repository import VideoRepository
from desktop_app.widgets.vector_index_panel import VectorIndexPanelWidget


def _setup_project_embeddings(tmp_path: Path):
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Vector Project",
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
                end_time=10,
                text="Machine learning basics",
                confidence=0.9,
            )
        ],
    )
    chunks = [
        KnowledgeChunk.create(
            transcript_id=transcript.id,
            start_time=float(index * 10),
            end_time=float(index * 10 + 9),
            chunk_text=f"Knowledge chunk {index}",
            topic_title="Machine Learning Basics",
            confidence=0.9,
        )
        for index in range(3)
    ]
    topics = [
        ChunkTopic.create(chunk_id=chunk.chunk_id, topic_title=chunk.topic_title, confidence=chunk.confidence)
        for chunk in chunks
    ]
    KnowledgeRepository(database.connection).replace_chunks(transcript.id, chunks, topics)
    embedding_repository = EmbeddingRepository(database.connection)
    model_name = DEFAULT_EMBEDDING_MODELS[0]
    embedding_repository.replace_embeddings(
        [
            EmbeddingRecord.create(
                chunk_id=chunk.chunk_id,
                model_name=model_name,
                vector=[1.0 if vector_index == index else 0.0 for vector_index in range(3)],
            )
            for index, chunk in enumerate(chunks)
        ]
    )
    return database, project, model_name


def test_embedding_model_selector_maps_explicit_sizes() -> None:
    selector = EmbeddingModelSelector()

    assert selector.select("small") == "BAAI/bge-small-en-v1.5"
    assert selector.select("base") == "BAAI/bge-base-en-v1.5"
    assert selector.select("large") == "BAAI/bge-large-en-v1.5"


def test_embedding_model_selector_auto_uses_ram_thresholds(monkeypatch) -> None:
    selector = EmbeddingModelSelector()

    monkeypatch.setattr(psutil, "virtual_memory", lambda: SimpleNamespace(total=8 * 1024**3))
    assert selector.select("auto") == "BAAI/bge-small-en-v1.5"
    monkeypatch.setattr(psutil, "virtual_memory", lambda: SimpleNamespace(total=16 * 1024**3))
    assert selector.select("auto") == "BAAI/bge-base-en-v1.5"
    monkeypatch.setattr(psutil, "virtual_memory", lambda: SimpleNamespace(total=32 * 1024**3))
    assert selector.select("auto") == "BAAI/bge-large-en-v1.5"


def test_vector_service_builds_faiss_index_and_persists_metadata(tmp_path) -> None:
    database, project, _model_name = _setup_project_embeddings(tmp_path)
    service = VectorService(VectorRepository(database.connection))

    result = service.build_project_index(
        project_id=project.id,
        project_workspace=tmp_path / "project",
        embedding_selection="small",
    )

    assert Path(result.record.index_path).exists()
    assert result.mapping_path.exists()
    assert result.vector_count == 3
    assert result.record.dimension == 3
    assert VectorRepository(database.connection).latest_for_project(project.id, result.record.embedding_model) is not None


def test_faiss_index_builder_round_trips_stats(tmp_path) -> None:
    builder = FaissIndexBuilder()
    result = builder.build_and_save(
        vectors=[[1.0, 0.0], [0.0, 1.0]],
        chunk_ids=["a", "b"],
        index_path=tmp_path / "index.faiss",
    )

    vector_count, dimension = builder.read_stats(result.index_path)

    assert vector_count == 2
    assert dimension == 2


def test_vector_panel_tracks_build_state(qapp) -> None:
    from desktop_app.vector_store.vector_manager import VectorIndexJobState, VectorIndexStatus

    widget = VectorIndexPanelWidget()
    widget.apply_state(
        VectorIndexJobState(
            job_id="job",
            project_id="project",
            embedding_selection="small",
            status=VectorIndexStatus.COMPLETED,
            progress_percent=100,
            vector_count=3,
            index_path="index.faiss",
        )
    )

    assert widget.progress_bar.value() == 100
    assert "3 vectors" in widget.status_label.text()
