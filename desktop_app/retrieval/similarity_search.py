from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


class SimilaritySearchError(RuntimeError):
    pass


@dataclass(frozen=True)
class SimilarityMatch:
    chunk_id: str
    rank: int
    raw_score: float
    similarity_score: float


class FaissSimilaritySearch:
    def search(self, *, index_path: Path, query_vector: list[float], top_k: int) -> list[SimilarityMatch]:
        if top_k <= 0:
            raise SimilaritySearchError("top_k must be greater than zero.")
        if not index_path.exists():
            raise SimilaritySearchError(f"FAISS index does not exist: {index_path}")
        mapping_path = index_path.with_suffix(".chunks.json")
        if not mapping_path.exists():
            raise SimilaritySearchError(f"FAISS chunk mapping does not exist: {mapping_path}")
        try:
            import faiss
            import numpy as np
        except ImportError as exc:
            raise SimilaritySearchError("faiss-cpu is required for retrieval search.") from exc

        mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
        chunk_ids = [str(chunk_id) for chunk_id in mapping.get("chunk_ids", [])]
        dimension = int(mapping.get("dimension", 0))
        if len(query_vector) != dimension:
            raise SimilaritySearchError(
                f"Query dimension {len(query_vector)} does not match FAISS dimension {dimension}."
            )
        index = faiss.read_index(str(index_path))
        matrix = np.asarray([query_vector], dtype="float32")
        faiss.normalize_L2(matrix)
        limit = min(top_k, len(chunk_ids))
        scores, indices = index.search(matrix, limit)
        matches: list[SimilarityMatch] = []
        for rank, (score, index_id) in enumerate(zip(scores[0], indices[0], strict=True), start=1):
            if index_id < 0 or index_id >= len(chunk_ids):
                continue
            raw_score = float(score)
            matches.append(
                SimilarityMatch(
                    chunk_id=chunk_ids[int(index_id)],
                    rank=rank,
                    raw_score=raw_score,
                    similarity_score=self.normalize_score(raw_score),
                )
            )
        return matches

    def normalize_score(self, raw_score: float) -> float:
        return max(0.0, min(1.0, (raw_score + 1.0) / 2.0))
