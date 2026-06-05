from __future__ import annotations

from desktop_app.embeddings.embedding_models import EMBEDDING_MODEL_BY_SIZE
from desktop_app.embeddings.embedding_worker import EmbeddingModelUnavailable
from desktop_app.embeddings.model_registry import EmbeddingModelRegistry


SUPPORTED_RETRIEVAL_MODELS = frozenset(EMBEDDING_MODEL_BY_SIZE.values())


class QueryEmbedder:
    def __init__(
        self,
        model_registry: EmbeddingModelRegistry | None = None,
        *,
        auto_unload_after_query: bool = False,
    ) -> None:
        self.model_registry = model_registry or EmbeddingModelRegistry.global_instance()
        self.auto_unload_after_query = auto_unload_after_query

    def embed(self, query: str, model_name: str) -> list[float]:
        cleaned = query.strip()
        if not cleaned:
            raise ValueError("Retrieval query cannot be empty.")
        if model_name not in SUPPORTED_RETRIEVAL_MODELS:
            raise EmbeddingModelUnavailable(f"Retrieval supports BGE Small/Base/Large only: {model_name}")
        try:
            vector = self.model_registry.encode(self._format_query(cleaned, model_name), model_name)
            return [float(value) for value in vector.tolist()]
        finally:
            if self.auto_unload_after_query:
                self.model_registry.unload_model(model_name)

    def _format_query(self, query: str, model_name: str) -> str:
        _ = model_name
        return f"Represent this sentence for searching relevant passages: {query}"
