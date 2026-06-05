from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class FaissIndexError(RuntimeError):
    pass


class FaissUnavailable(FaissIndexError):
    pass


@dataclass(frozen=True)
class FaissIndexBuildResult:
    index_path: Path
    mapping_path: Path
    vector_count: int
    dimension: int


class FaissIndexBuilder:
    def build_and_save(
        self,
        *,
        vectors: list[list[float]],
        chunk_ids: list[str],
        index_path: Path,
    ) -> FaissIndexBuildResult:
        if not vectors:
            raise FaissIndexError("No embeddings are available for FAISS indexing.")
        if len(vectors) != len(chunk_ids):
            raise FaissIndexError("Embedding vector count does not match chunk mapping count.")
        dimension = len(vectors[0])
        if dimension <= 0:
            raise FaissIndexError("Embedding vectors must have a positive dimension.")
        if any(len(vector) != dimension for vector in vectors):
            raise FaissIndexError("All embedding vectors must have the same dimension.")

        try:
            import faiss
            import numpy as np
        except ImportError as exc:
            raise FaissUnavailable("faiss-cpu is required to build local vector indexes.") from exc

        matrix = np.asarray(vectors, dtype="float32")
        faiss.normalize_L2(matrix)
        index = faiss.IndexFlatIP(dimension)
        index.add(matrix)

        index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(index, str(index_path))
        mapping_path = index_path.with_suffix(".chunks.json")
        mapping_path.write_text(
            json.dumps(
                {
                    "dimension": dimension,
                    "vector_count": len(chunk_ids),
                    "chunk_ids": chunk_ids,
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        return FaissIndexBuildResult(
            index_path=index_path,
            mapping_path=mapping_path,
            vector_count=len(chunk_ids),
            dimension=dimension,
        )

    def read_stats(self, index_path: Path) -> tuple[int, int]:
        try:
            import faiss
        except ImportError as exc:
            raise FaissUnavailable("faiss-cpu is required to read local vector indexes.") from exc
        index = faiss.read_index(str(index_path))
        return int(index.ntotal), int(index.d)
