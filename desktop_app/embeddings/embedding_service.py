from __future__ import annotations

from collections.abc import Callable

from desktop_app.embeddings.embedding_models import EmbeddingRecord
from desktop_app.embeddings.embedding_repository import EmbeddingRepository
from desktop_app.embeddings.embedding_worker import CancellationToken, LocalEmbeddingWorker
from desktop_app.knowledge.knowledge_models import KnowledgeChunk
from desktop_app.knowledge.knowledge_repository import KnowledgeRepository


class EmbeddingService:
    def __init__(
        self,
        embedding_repository: EmbeddingRepository,
        knowledge_repository: KnowledgeRepository,
        worker: LocalEmbeddingWorker | None = None,
    ) -> None:
        self.embedding_repository = embedding_repository
        self.knowledge_repository = knowledge_repository
        self.worker = worker or LocalEmbeddingWorker()

    def generate_for_transcript(
        self,
        transcript_id: str,
        model_name: str,
        cancellation_token: CancellationToken | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> list[EmbeddingRecord]:
        chunks = self.knowledge_repository.list_chunks(transcript_id)
        return self.generate_for_chunks(chunks, model_name, cancellation_token, progress_callback)

    def generate_for_chunks(
        self,
        chunks: list[KnowledgeChunk],
        model_name: str,
        cancellation_token: CancellationToken | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> list[EmbeddingRecord]:
        records = self.worker.generate(chunks, model_name, cancellation_token, progress_callback)
        self.embedding_repository.replace_embeddings(records)
        return records

    def count_for_transcript(self, transcript_id: str, model_name: str) -> int:
        chunks = self.knowledge_repository.list_chunks(transcript_id)
        return self.embedding_repository.count_for_chunks([chunk.chunk_id for chunk in chunks], model_name)
