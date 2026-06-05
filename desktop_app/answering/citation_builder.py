from __future__ import annotations

import json

from desktop_app.answering.answer_models import Citation
from desktop_app.evidence.evidence_models import EvidenceItem


class CitationBuilder:
    def build(self, evidence_items: list[EvidenceItem]) -> list[Citation]:
        citations: list[Citation] = []
        for index, item in enumerate(evidence_items, start=1):
            citations.append(
                Citation(
                    citation_id=index,
                    source_video=item.source.video_name,
                    chunk_id=item.chunk_id,
                    timestamp_start=item.start_time,
                    timestamp_end=item.end_time,
                    confidence=item.confidence_score,
                    source_video_id=item.source.video_id,
                    source_file_path=item.source.file_path,
                )
            )
        return citations

    def append_citation_block(self, answer: str, citations: list[Citation]) -> str:
        if not citations:
            return answer.strip()
        citation_lines = [
            f"{citation.label()} · chunk {citation.chunk_id} · confidence {citation.confidence:.3f}"
            for citation in citations
        ]
        return f"{answer.strip()}\n\nCitations:\n" + "\n".join(citation_lines)

    def to_json(self, citations: list[Citation]) -> str:
        return json.dumps(
            [
                {
                    "citation_id": citation.citation_id,
                    "source_video": citation.source_video,
                    "chunk_id": citation.chunk_id,
                    "timestamp_start": citation.timestamp_start,
                    "timestamp_end": citation.timestamp_end,
                    "confidence": citation.confidence,
                    "source_video_id": citation.source_video_id,
                    "source_file_path": citation.source_file_path,
                }
                for citation in citations
            ],
            indent=2,
        )
