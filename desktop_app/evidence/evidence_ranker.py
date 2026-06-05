from __future__ import annotations

from desktop_app.evidence.evidence_models import EvidenceItem


class EvidenceRanker:
    def rank(self, items: list[EvidenceItem]) -> list[EvidenceItem]:
        ranked = sorted(
            items,
            key=lambda item: (
                item.confidence_score,
                item.similarity_score,
                -item.retrieval_rank,
                -item.start_time,
            ),
            reverse=True,
        )
        return [
            EvidenceItem.create(
                project_id=item.project_id,
                query=item.query,
                chunk_id=item.chunk_id,
                retrieval_rank=index,
                source=item.source,
                topic_title=item.topic_title,
                start_time=item.start_time,
                end_time=item.end_time,
                similarity_score=item.similarity_score,
                confidence_score=item.confidence_score,
                chunk_text=item.chunk_text,
            )
            for index, item in enumerate(ranked, start=1)
        ]
