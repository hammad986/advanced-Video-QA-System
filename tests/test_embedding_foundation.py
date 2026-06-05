from __future__ import annotations

import pytest

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.embeddings.embedding_models import (
    DEFAULT_EMBEDDING_MODELS,
    EmbeddingJobState,
    EmbeddingRecord,
    EmbeddingStatus,
    deserialize_vector,
    serialize_vector,
)
from desktop_app.embeddings.embedding_worker import LocalEmbeddingWorker
from desktop_app.embeddings.model_registry import EmbeddingModelRegistry
from desktop_app.embeddings.embedding_repository import EmbeddingRepository
from desktop_app.embeddings.embedding_service import EmbeddingService
from desktop_app.embeddings.embedding_worker import CancellationToken, EmbeddingCancelled
from desktop_app.retrieval.query_embedder import QueryEmbedder
from desktop_app.knowledge.knowledge_models import ChunkTopic, KnowledgeChunk
from desktop_app.knowledge.knowledge_repository import KnowledgeRepository
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.transcripts.transcript_models import Transcript, TranscriptSegment, TranscriptStatus
from desktop_app.transcripts.transcript_repository import TranscriptRepository
from desktop_app.videos.video_metadata import VideoMetadata
from desktop_app.videos.video_model import VideoRecord
from desktop_app.videos.video_repository import VideoRepository
from desktop_app.widgets.embedding_panel import EmbeddingPanelWidget


class FakeEmbeddingWorker:
    def generate(self, chunks, model_name, cancellation_token=None, progress_callback=None):
        token = cancellation_token or CancellationToken()
        token.raise_if_cancelled()
        if progress_callback is not None:
            progress_callback(50, "Fake embeddings generated")
        return [
            EmbeddingRecord.create(
                chunk_id=chunk.chunk_id,
                model_name=model_name,
                vector=[float(index), float(index + 1), float(index + 2)],
            )
            for index, chunk in enumerate(chunks)
        ]


class CancellingEmbeddingWorker:
    def generate(self, chunks, model_name, cancellation_token=None, progress_callback=None):
        token = cancellation_token or CancellationToken()
        token.cancel()
        token.raise_if_cancelled()
        return []


def _setup_chunks(tmp_path):
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project_service = ProjectService(ProjectRepository(database.connection))
    project = project_service.create_project(name="Embedding Project", root_path=str(tmp_path / "project"))
    video_path = tmp_path / "lecture.mp4"
    video_path.write_bytes(b"video")
    video = VideoRepository(database.connection).save(
        VideoRecord.create(
            project_id=project.id,
            name=video_path.name,
            file_path=str(video_path),
            file_size=video_path.stat().st_size,
            metadata=VideoMetadata(duration=120.0, fps=30.0, width=1280, height=720),
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
                end_time=30,
                text="Machine learning basics and unsupervised learning.",
                confidence=0.9,
            )
        ],
    )
    chunks = [
        KnowledgeChunk.create(
            transcript_id=transcript.id,
            start_time=0,
            end_time=30,
            chunk_text="Machine learning basics and unsupervised learning.",
            topic_title="Machine Learning Basics",
            confidence=0.9,
        ),
        KnowledgeChunk.create(
            transcript_id=transcript.id,
            start_time=30,
            end_time=60,
            chunk_text="Clustering groups similar examples without labels.",
            topic_title="Clustering",
            confidence=0.86,
        ),
    ]
    topics = [
        ChunkTopic.create(chunk_id=chunk.chunk_id, topic_title=chunk.topic_title, confidence=chunk.confidence)
        for chunk in chunks
    ]
    knowledge_repository = KnowledgeRepository(database.connection)
    knowledge_repository.replace_chunks(transcript.id, chunks, topics)
    return database, transcript, chunks, knowledge_repository


def test_embedding_vector_serialization_round_trip() -> None:
    vector = [0.1, -0.2, 0.3]

    restored = deserialize_vector(serialize_vector(vector))

    assert restored == pytest.approx(vector)


def test_embedding_repository_persists_blob_records(tmp_path) -> None:
    database, _transcript, chunks, _knowledge_repository = _setup_chunks(tmp_path)
    repository = EmbeddingRepository(database.connection)
    record = EmbeddingRecord.create(
        chunk_id=chunks[0].chunk_id,
        model_name=DEFAULT_EMBEDDING_MODELS[0],
        vector=[1.0, 2.0, 3.0],
    )

    repository.save_embedding(record)
    persisted = repository.get_by_chunk_and_model(chunks[0].chunk_id, DEFAULT_EMBEDDING_MODELS[0])

    assert persisted is not None
    assert persisted.dimension == 3
    assert persisted.vector() == pytest.approx([1.0, 2.0, 3.0])


def test_embedding_service_generates_and_persists_for_knowledge_chunks(tmp_path) -> None:
    database, transcript, chunks, knowledge_repository = _setup_chunks(tmp_path)
    repository = EmbeddingRepository(database.connection)
    service = EmbeddingService(repository, knowledge_repository, worker=FakeEmbeddingWorker())

    records = service.generate_for_transcript(transcript.id, DEFAULT_EMBEDDING_MODELS[0])

    assert len(records) == len(chunks)
    assert repository.count_for_chunks([chunk.chunk_id for chunk in chunks], DEFAULT_EMBEDDING_MODELS[0]) == len(chunks)


def test_embedding_generation_can_be_cancelled(tmp_path) -> None:
    database, transcript, _chunks, knowledge_repository = _setup_chunks(tmp_path)
    service = EmbeddingService(
        EmbeddingRepository(database.connection),
        knowledge_repository,
        worker=CancellingEmbeddingWorker(),
    )

    with pytest.raises(EmbeddingCancelled):
        service.generate_for_transcript(transcript.id, DEFAULT_EMBEDDING_MODELS[0])


def test_embedding_panel_tracks_progress(qapp) -> None:
    widget = EmbeddingPanelWidget()
    model_name = widget.selected_model()

    widget.apply_state(
        EmbeddingJobState(
            job_id="job",
            transcript_id="transcript",
            model_name=model_name,
            status=EmbeddingStatus.RUNNING,
            progress_percent=50,
        )
    )

    assert model_name == DEFAULT_EMBEDDING_MODELS[0]
    assert widget.progress_bar.value() == 50
    assert widget.cancel_button.isEnabled()


def test_embedding_and_query_paths_can_share_model_registry() -> None:
    registry = EmbeddingModelRegistry()
    worker = LocalEmbeddingWorker(model_registry=registry)
    query_embedder = QueryEmbedder(model_registry=registry)

    assert worker.model_registry is registry
    assert query_embedder.model_registry is registry
    assert registry.loaded_model_count() == 0
