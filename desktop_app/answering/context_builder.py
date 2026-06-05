from __future__ import annotations

from dataclasses import dataclass

from desktop_app.evidence.evidence_models import EvidenceItem


@dataclass(frozen=True)
class GroundedContext:
    prompt_context: str
    evidence_items: list[EvidenceItem]
    sufficient: bool


class ContextBuilder:
    MIN_CONFIDENCE = 0.55

    def build(self, *, question: str, evidence_items: list[EvidenceItem]) -> GroundedContext:
        usable_items = [
            item
            for item in evidence_items
            if item.confidence_score >= self.MIN_CONFIDENCE and item.chunk_text.strip()
        ]
        if not usable_items:
            return GroundedContext(prompt_context="", evidence_items=[], sufficient=False)
        lines = []
        for index, item in enumerate(usable_items, start=1):
            lines.append(
                "\n".join(
                    (
                        f"[{index}] Source Video: {item.source.video_name}",
                        f"Chunk ID: {item.chunk_id}",
                        f"Timestamp: {item.start_time:.1f}s - {item.end_time:.1f}s",
                        f"Confidence: {item.confidence_score:.3f}",
                        f"Evidence Text: {item.chunk_text}",
                    )
                )
            )
        prompt_context = (
            "Use ONLY the evidence below. If the evidence does not directly support the answer, "
            "return exactly: I could not find enough evidence in the loaded videos.\n"
            "Every factual sentence must include at least one citation marker like [1].\n\n"
            f"Question: {question}\n\nEvidence:\n" + "\n\n".join(lines)
        )
        return GroundedContext(prompt_context=prompt_context, evidence_items=usable_items, sufficient=True)
