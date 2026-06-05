from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import psutil

from desktop_app.embeddings.embedding_models import EMBEDDING_MODEL_BY_SIZE
from desktop_app.vector_store.faiss_index import FaissIndexBuilder
from desktop_app.vector_store.vector_repository import VectorIndexRecord, VectorRepository


class VectorStoreError(RuntimeError):
    pass


@dataclass(frozen=True)
class VectorBuildResult:
    record: VectorIndexRecord
    vector_count: int
    mapping_path: Path


class EmbeddingModelSelector:
    def select(self, selection: str) -> str:
        normalized = selection.strip().lower() or "auto"
        if normalized == "auto":
            normalized = self.auto_size()
        try:
            return EMBEDDING_MODEL_BY_SIZE[normalized]
        except KeyError as exc:
            raise VectorStoreError(f"Unsupported embedding selection: {selection}") from exc

    def auto_size(self) -> str:
        ram_gb = psutil.virtual_memory().total / (1024**3)
        if ram_gb < 12:
            return "small"
        if ram_gb <= 24:
            return "base"
        return "large"


class VectorService:
    def __init__(
        self,
        vector_repository: VectorRepository,
        *,
        index_builder: FaissIndexBuilder | None = None,
        model_selector: EmbeddingModelSelector | None = None,
    ) -> None:
        self.vector_repository = vector_repository
        self.index_builder = index_builder or FaissIndexBuilder()
        self.model_selector = model_selector or EmbeddingModelSelector()

    def build_project_index(
        self,
        *,
        project_id: str,
        project_workspace: Path,
        embedding_selection: str,
    ) -> VectorBuildResult:
        embedding_model = self.model_selector.select(embedding_selection)
        embeddings = self.vector_repository.list_project_embeddings(project_id, embedding_model)
        if not embeddings:
            raise VectorStoreError(f"No embeddings found for {embedding_model}. Generate embeddings before indexing.")
        vectors = [embedding.vector for embedding in embeddings]
        chunk_ids = [embedding.chunk_id for embedding in embeddings]
        dimension = len(vectors[0])
        index_dir = project_workspace / "VectorIndexes"
        safe_model_name = embedding_model.replace("/", "__")
        index_path = index_dir / f"{safe_model_name}.faiss"
        build_result = self.index_builder.build_and_save(
            vectors=vectors,
            chunk_ids=chunk_ids,
            index_path=index_path,
        )
        record = VectorIndexRecord.create(
            project_id=project_id,
            embedding_model=embedding_model,
            dimension=dimension,
            index_path=str(build_result.index_path),
        )
        self.vector_repository.save_index(record)
        return VectorBuildResult(
            record=record,
            vector_count=build_result.vector_count,
            mapping_path=build_result.mapping_path,
        )

    def latest_index(self, project_id: str, embedding_selection: str) -> VectorIndexRecord | None:
        embedding_model = self.model_selector.select(embedding_selection)
        return self.vector_repository.latest_for_project(project_id, embedding_model)
