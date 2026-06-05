from __future__ import annotations

import time

from desktop_app.evidence.evidence_models import EvidenceHistoryRecord, EvidenceItem, EvidenceResult
from desktop_app.evidence.evidence_ranker import EvidenceRanker
from desktop_app.evidence.evidence_repository import EvidenceRepository
from desktop_app.retrieval.retrieval_service import RetrievalService


class EvidenceError(RuntimeError):
    pass


class EvidenceService:
    def __init__(
        self,
        evidence_repository: EvidenceRepository,
        retrieval_service: RetrievalService,
        *,
        ranker: EvidenceRanker | None = None,
    ) -> None:
        self.evidence_repository = evidence_repository
        self.retrieval_service = retrieval_service
        self.ranker = ranker or EvidenceRanker()
        self.last_retrieval_count = 0

    def generate(
        self,
        *,
        project_id: str,
        query: str,
        embedding_selection: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> EvidenceResult:
        started = time.perf_counter()
        retrieval_result = self.retrieval_service.search(
            project_id=project_id,
            query=query,
            embedding_selection=embedding_selection,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        self.last_retrieval_count = len(retrieval_result.hits)
        chunk_ids = [hit.chunk.chunk_id for hit in retrieval_result.hits]
        sources = self.evidence_repository.get_sources(chunk_ids)
        items: list[EvidenceItem] = []
        for hit in retrieval_result.hits:
            source = sources.get(hit.chunk.chunk_id)
            if source is None:
                continue
            items.append(
                EvidenceItem.create(
                    project_id=project_id,
                    query=query,
                    chunk_id=hit.chunk.chunk_id,
                    retrieval_rank=hit.rank,
                    source=source,
                    topic_title=hit.chunk.topic_title,
                    start_time=hit.chunk.start_time,
                    end_time=hit.chunk.end_time,
                    similarity_score=hit.similarity_score,
                    confidence_score=hit.confidence_score,
                    chunk_text=hit.chunk.chunk_text,
                )
            )
        ranked_items = self.ranker.rank(items)
        self.evidence_repository.save_history([EvidenceHistoryRecord.from_item(item) for item in ranked_items])
        return EvidenceResult(
            project_id=project_id,
            query=query,
            duration_ms=(time.perf_counter() - started) * 1000,
            items=ranked_items,
        )
