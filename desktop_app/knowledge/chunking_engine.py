from __future__ import annotations

import re

from desktop_app.knowledge.knowledge_models import ChunkDraft
from desktop_app.transcripts.transcript_models import TranscriptSegment


class KnowledgeStructuringError(RuntimeError):
    pass


class SemanticChunkingEngine:
    STOPWORDS = {
        "the", "a", "an", "and", "or", "of", "to", "in", "is", "it", "for", "on", "with", "that",
        "this", "you", "we", "are", "be", "as", "by", "at", "from", "have", "has", "was", "were",
    }
    TOPIC_CUES = {
        "introduction", "overview", "next", "now", "let's", "supervised", "unsupervised",
        "neural", "evaluation", "training", "data", "practical", "example",
    }

    def __init__(
        self,
        *,
        min_chunk_words: int = 45,
        max_chunk_words: int = 260,
        similarity_threshold: float = 0.12,
    ) -> None:
        self.min_chunk_words = min_chunk_words
        self.max_chunk_words = max_chunk_words
        self.similarity_threshold = similarity_threshold

    def chunk(self, segments: list[TranscriptSegment]) -> list[ChunkDraft]:
        usable = [segment for segment in segments if segment.text.strip()]
        if not usable:
            raise KnowledgeStructuringError("Transcript has no usable text segments.")

        chunks: list[ChunkDraft] = []
        current: list[TranscriptSegment] = []
        current_terms: set[str] = set()

        for segment in usable:
            segment_terms = self._terms(segment.text)
            current_text = " ".join(item.text for item in current)
            current_words = len(current_text.split())
            similarity = self._jaccard(current_terms, segment_terms)
            starts_new_topic = self._has_topic_cue(segment.text)
            too_large = current_words + len(segment.text.split()) > self.max_chunk_words
            semantic_break = current and current_words >= self.min_chunk_words and (
                too_large or (starts_new_topic and similarity < 0.35) or similarity < self.similarity_threshold
            )

            if semantic_break:
                chunks.append(self._draft_from_segments(current))
                current = []
                current_terms = set()

            current.append(segment)
            current_terms.update(segment_terms)

        if current:
            chunks.append(self._draft_from_segments(current))

        return self._merge_tiny_chunks(chunks)

    def _draft_from_segments(self, segments: list[TranscriptSegment]) -> ChunkDraft:
        text = " ".join(segment.text.strip() for segment in segments if segment.text.strip())
        if not text:
            raise KnowledgeStructuringError("Cannot create an empty knowledge chunk.")
        confidence_values = [segment.confidence for segment in segments if segment.confidence > 0]
        confidence = sum(confidence_values) / len(confidence_values) if confidence_values else 0.75
        return ChunkDraft(
            start_time=segments[0].start_time,
            end_time=segments[-1].end_time,
            chunk_text=text,
            confidence=confidence,
        )

    def _merge_tiny_chunks(self, chunks: list[ChunkDraft]) -> list[ChunkDraft]:
        if not chunks:
            return []
        merged: list[ChunkDraft] = []
        pending: ChunkDraft | None = None
        for chunk in chunks:
            if pending is None:
                pending = chunk
                continue
            if len(pending.chunk_text.split()) < self.min_chunk_words:
                combined_text = f"{pending.chunk_text} {chunk.chunk_text}".strip()
                pending = ChunkDraft(
                    start_time=pending.start_time,
                    end_time=chunk.end_time,
                    chunk_text=combined_text,
                    confidence=(pending.confidence + chunk.confidence) / 2,
                )
            else:
                merged.append(pending)
                pending = chunk
        if pending is not None:
            merged.append(pending)
        return merged

    def _terms(self, text: str) -> set[str]:
        words = re.findall(r"[a-zA-Z][a-zA-Z'-]{2,}", text.lower())
        return {word for word in words if word not in self.STOPWORDS}

    def _jaccard(self, left: set[str], right: set[str]) -> float:
        if not left or not right:
            return 0.0
        return len(left & right) / len(left | right)

    def _has_topic_cue(self, text: str) -> bool:
        lowered = text.lower()
        return any(cue in lowered for cue in self.TOPIC_CUES)

