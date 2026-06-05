from __future__ import annotations

import threading
from collections.abc import Callable
from typing import TYPE_CHECKING

from desktop_app.embeddings.embedding_models import EmbeddingRecord, SUPPORTED_EMBEDDING_MODELS
from desktop_app.knowledge.knowledge_models import KnowledgeChunk

if TYPE_CHECKING:
    from desktop_app.embeddings.model_registry import EmbeddingModelRegistry


class EmbeddingError(RuntimeError):
    pass


class EmbeddingCancelled(EmbeddingError):
    pass


class EmbeddingModelUnavailable(EmbeddingError):
    pass


class CancellationToken:
    def __init__(self) -> None:
        self._event = threading.Event()

    def cancel(self) -> None:
        self._event.set()

    def is_cancelled(self) -> bool:
        return self._event.is_set()

    def raise_if_cancelled(self) -> None:
        if self.is_cancelled():
            raise EmbeddingCancelled("Embedding generation was cancelled.")


class LocalEmbeddingWorker:
    def __init__(
        self,
        model_registry: "EmbeddingModelRegistry | None" = None,
        *,
        batch_size: int = 32,
        auto_unload_after_generate: bool = False,
    ) -> None:
        if model_registry is None:
            from desktop_app.embeddings.model_registry import EmbeddingModelRegistry

            model_registry = EmbeddingModelRegistry.global_instance()
        self.model_registry = model_registry
        self.batch_size = max(1, batch_size)
        self.auto_unload_after_generate = auto_unload_after_generate

    def generate(
        self,
        chunks: list[KnowledgeChunk],
        model_name: str,
        cancellation_token: CancellationToken | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ) -> list[EmbeddingRecord]:
        token = cancellation_token or CancellationToken()
        token.raise_if_cancelled()
        if model_name not in SUPPORTED_EMBEDDING_MODELS:
            raise EmbeddingModelUnavailable(f"Unsupported embedding model: {model_name}")
        if not chunks:
            return []

        self.model_registry.get_model(model_name)
        token.raise_if_cancelled()
        progress_callback = progress_callback or (lambda _percent, _message: None)
        texts = [self._format_text(chunk, model_name) for chunk in chunks]
        progress_callback(10, "Embedding model loaded")
        try:
            vectors = self.model_registry.encode(texts, model_name, batch_size=self.batch_size)
        finally:
            if self.auto_unload_after_generate:
                self.model_registry.unload_model(model_name)
        token.raise_if_cancelled()
        records: list[EmbeddingRecord] = []
        total = len(chunks)
        for index, (chunk, vector) in enumerate(zip(chunks, vectors, strict=True), start=1):
            token.raise_if_cancelled()
            records.append(
                EmbeddingRecord.create(
                    chunk_id=chunk.chunk_id,
                    model_name=model_name,
                    vector=[float(value) for value in vector.tolist()],
                )
            )
            progress_callback(10 + int((index / total) * 90), f"Embedded {index}/{total} chunks")
        return records

    def _format_text(self, chunk: KnowledgeChunk, model_name: str) -> str:
        if model_name.startswith("intfloat/e5-"):
            return f"passage: {chunk.chunk_text}"
        return chunk.chunk_text
