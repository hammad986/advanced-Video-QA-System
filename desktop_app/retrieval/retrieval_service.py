from __future__ import annotations

import re
import time
from pathlib import Path

from desktop_app.retrieval.query_embedder import QueryEmbedder
from desktop_app.retrieval.retrieval_models import RetrievalHistoryRecord, RetrievalHit, RetrievalResult
from desktop_app.retrieval.retrieval_repository import RetrievalRepository
from desktop_app.retrieval.similarity_search import FaissSimilaritySearch, SimilarityMatch
from desktop_app.vector_store.vector_repository import VectorRepository
from desktop_app.vector_store.vector_service import EmbeddingModelSelector


class RetrievalError(RuntimeError):
    pass


class RetrievalService:
    def __init__(
        self,
        retrieval_repository: RetrievalRepository,
        vector_repository: VectorRepository,
        *,
        query_embedder: QueryEmbedder | None = None,
        similarity_search: FaissSimilaritySearch | None = None,
        model_selector: EmbeddingModelSelector | None = None,
    ) -> None:
        self.retrieval_repository = retrieval_repository
        self.vector_repository = vector_repository
        self.query_embedder = query_embedder or QueryEmbedder()
        self.similarity_search = similarity_search or FaissSimilaritySearch()
        self.model_selector = model_selector or EmbeddingModelSelector()

    def search(
        self,
        *,
        project_id: str,
        query: str,
        embedding_selection: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> RetrievalResult:
        started = time.perf_counter()
        embedding_model = self.model_selector.select(embedding_selection)
        index_record = self.vector_repository.latest_for_project(project_id, embedding_model)
        if index_record is None:
            raise RetrievalError(f"No FAISS index found for {embedding_model}. Build the vector index first.")
        query_vector = self.query_embedder.embed(query, embedding_model)
        matches = self.similarity_search.search(
            index_path=Path(index_record.index_path),
            query_vector=query_vector,
            top_k=max(top_k * 3, top_k),
        )
        hits = self._rank_matches(query=query, matches=matches, min_similarity=min_similarity, top_k=top_k)
        duration_ms = (time.perf_counter() - started) * 1000
        self.retrieval_repository.save_history(
            RetrievalHistoryRecord.create(
                project_id=project_id,
                query=query,
                embedding_model=embedding_model,
                top_k=top_k,
                duration_ms=duration_ms,
            )
        )
        return RetrievalResult(
            project_id=project_id,
            query=query,
            embedding_model=embedding_model,
            top_k=top_k,
            duration_ms=duration_ms,
            hits=hits,
        )

    def _rank_matches(
        self,
        *,
        query: str,
        matches: list[SimilarityMatch],
        min_similarity: float,
        top_k: int,
    ) -> list[RetrievalHit]:
        unique_matches: dict[str, SimilarityMatch] = {}
        for match in matches:
            if match.similarity_score < min_similarity:
                continue
            old = unique_matches.get(match.chunk_id)
            if old is None or match.similarity_score > old.similarity_score:
                unique_matches[match.chunk_id] = match
        chunks = self.retrieval_repository.get_chunks(list(unique_matches))
        query_terms = self._terms(query)
        ranked: list[RetrievalHit] = []
        for match in unique_matches.values():
            chunk = chunks.get(match.chunk_id)
            if chunk is None:
                continue
            topic_score = self._topic_score(query_terms, chunk.topic_title)
            confidence_score = min(1.0, (match.similarity_score * 0.85) + (topic_score * 0.15))
            ranked.append(
                RetrievalHit(
                    chunk=chunk,
                    rank=0,
                    raw_score=match.raw_score,
                    similarity_score=match.similarity_score,
                    confidence_score=confidence_score,
                    topic_score=topic_score,
                )
            )
        ranked.sort(key=lambda hit: (hit.confidence_score, hit.similarity_score, hit.chunk.confidence), reverse=True)
        return [
            RetrievalHit(
                chunk=hit.chunk,
                rank=index,
                raw_score=hit.raw_score,
                similarity_score=hit.similarity_score,
                confidence_score=hit.confidence_score,
                topic_score=hit.topic_score,
            )
            for index, hit in enumerate(ranked[:top_k], start=1)
        ]

    def _topic_score(self, query_terms: set[str], topic_title: str) -> float:
        topic_terms = self._terms(topic_title)
        if not query_terms or not topic_terms:
            return 0.0
        return len(query_terms & topic_terms) / len(query_terms | topic_terms)

    def _terms(self, text: str) -> set[str]:
        return {
            term
            for term in re.findall(r"[a-z0-9]+", text.lower())
            if len(term) > 2 and term not in {"the", "and", "for", "with", "what", "how", "why"}
        }
