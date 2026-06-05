from __future__ import annotations

from pathlib import Path

import pytest

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.embeddings.embedding_models import DEFAULT_EMBEDDING_MODELS, EmbeddingRecord
from desktop_app.embeddings.embedding_repository import EmbeddingRepository
from desktop_app.knowledge.knowledge_models import ChunkTopic, KnowledgeChunk
from desktop_app.knowledge.knowledge_repository import KnowledgeRepository
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.retrieval.query_embedder import QueryEmbedder
from desktop_app.retrieval.retrieval_repository import RetrievalRepository
from desktop_app.retrieval.retrieval_service import RetrievalService
from desktop_app.retrieval.similarity_search import FaissSimilaritySearch
from desktop_app.transcripts.transcript_models import Transcript, TranscriptSegment, TranscriptStatus
from desktop_app.transcripts.transcript_repository import TranscriptRepository
from desktop_app.vector_store.vector_repository import VectorRepository
from desktop_app.vector_store.vector_service import VectorService
from desktop_app.videos.video_metadata import VideoMetadata
from desktop_app.videos.video_model import VideoRecord
from desktop_app.videos.video_repository import VideoRepository


class FakeQueryEmbedder:
    def __init__(self, vector: list[float]) -> None:
        self.vector = vector
        self.model_names: list[str] = []

    def embed(self, query: str, model_name: str) -> list[float]:
        self.model_names.append(model_name)
        return self.vector


def _setup_retrieval_project(tmp_path: Path):
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Retrieval Project",
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
            metadata=VideoMetadata(duration=90.0, fps=30.0, width=1280, height=720),
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
            chunk_text="Neural networks use layers and activations.",
            topic_title="Neural Networks",
            confidence=0.9,
        ),
        KnowledgeChunk.create(
            transcript_id=transcript.id,
            start_time=40,
            end_time=60,
            chunk_text="Model evaluation uses validation accuracy and precision.",
            topic_title="Model Evaluation",
            confidence=0.88,
        ),
    ]
    topics = [
        ChunkTopic.create(chunk_id=chunk.chunk_id, topic_title=chunk.topic_title, confidence=chunk.confidence)
        for chunk in chunks
    ]
    KnowledgeRepository(database.connection).replace_chunks(transcript.id, chunks, topics)
    model_name = DEFAULT_EMBEDDING_MODELS[0]
    EmbeddingRepository(database.connection).replace_embeddings(
        [
            EmbeddingRecord.create(chunk_id=chunks[0].chunk_id, model_name=model_name, vector=[1.0, 0.0, 0.0]),
            EmbeddingRecord.create(chunk_id=chunks[1].chunk_id, model_name=model_name, vector=[0.0, 1.0, 0.0]),
            EmbeddingRecord.create(chunk_id=chunks[2].chunk_id, model_name=model_name, vector=[0.0, 0.0, 1.0]),
        ]
    )
    vector_service = VectorService(VectorRepository(database.connection))
    vector_service.build_project_index(
        project_id=project.id,
        project_workspace=tmp_path / "project",
        embedding_selection="small",
    )
    return database, project, chunks


def test_similarity_search_returns_top_k_matches(tmp_path) -> None:
    database, project, chunks = _setup_retrieval_project(tmp_path)
    index_record = VectorRepository(database.connection).latest_for_project(project.id, DEFAULT_EMBEDDING_MODELS[0])

    matches = FaissSimilaritySearch().search(
        index_path=Path(index_record.index_path),
        query_vector=[1.0, 0.0, 0.0],
        top_k=2,
    )

    assert len(matches) == 2
    assert matches[0].chunk_id == chunks[0].chunk_id
    assert matches[0].similarity_score >= matches[1].similarity_score


def test_retrieval_service_uses_index_model_and_persists_history(tmp_path) -> None:
    database, project, chunks = _setup_retrieval_project(tmp_path)
    query_embedder = FakeQueryEmbedder([1.0, 0.0, 0.0])
    repository = RetrievalRepository(database.connection)
    service = RetrievalService(
        repository,
        VectorRepository(database.connection),
        query_embedder=query_embedder,
    )

    result = service.search(
        project_id=project.id,
        query="machine learning basics",
        embedding_selection="small",
        top_k=2,
        min_similarity=0.0,
    )
    history = repository.list_history(project.id)

    assert result.embedding_model == DEFAULT_EMBEDDING_MODELS[0]
    assert query_embedder.model_names == [DEFAULT_EMBEDDING_MODELS[0]]
    assert result.hits[0].chunk.chunk_id == chunks[0].chunk_id
    assert result.hits[0].rank == 1
    assert result.hits[0].confidence_score >= result.hits[1].confidence_score
    assert history and history[0].query == "machine learning basics"


def test_retrieval_service_applies_min_similarity_threshold(tmp_path) -> None:
    database, project, _chunks = _setup_retrieval_project(tmp_path)
    service = RetrievalService(
        RetrievalRepository(database.connection),
        VectorRepository(database.connection),
        query_embedder=FakeQueryEmbedder([0.0, 1.0, 0.0]),
    )

    result = service.search(
        project_id=project.id,
        query="neural networks",
        embedding_selection="small",
        top_k=5,
        min_similarity=0.99,
    )

    assert len(result.hits) == 1
    assert result.hits[0].chunk.topic_title == "Neural Networks"


def test_query_embedder_rejects_non_bge_models() -> None:
    embedder = QueryEmbedder()

    with pytest.raises(Exception):
        embedder.embed("test", "intfloat/e5-small-v2")
