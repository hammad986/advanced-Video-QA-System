from __future__ import annotations

from dataclasses import dataclass

from desktop_app.transcripts.transcript_models import TranscriptSegment


@dataclass(frozen=True)
class TranscriptSearchResult:
    query: str
    indices: list[int]
    current_position: int = 0

    @property
    def current_index(self) -> int | None:
        if not self.indices:
            return None
        return self.indices[self.current_position]


class TranscriptSearchEngine:
    def search(self, segments: list[TranscriptSegment], query: str) -> TranscriptSearchResult:
        normalized = query.strip().lower()
        if not normalized:
            return TranscriptSearchResult(query=query, indices=[])
        indices = [
            index
            for index, segment in enumerate(segments)
            if normalized in segment.text.lower()
        ]
        return TranscriptSearchResult(query=query, indices=indices)

    def next_result(self, result: TranscriptSearchResult) -> TranscriptSearchResult:
        if not result.indices:
            return result
        return TranscriptSearchResult(
            query=result.query,
            indices=result.indices,
            current_position=(result.current_position + 1) % len(result.indices),
        )

    def previous_result(self, result: TranscriptSearchResult) -> TranscriptSearchResult:
        if not result.indices:
            return result
        return TranscriptSearchResult(
            query=result.query,
            indices=result.indices,
            current_position=(result.current_position - 1) % len(result.indices),
        )

