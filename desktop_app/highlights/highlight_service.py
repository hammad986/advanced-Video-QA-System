from __future__ import annotations

from desktop_app.evidence.evidence_models import EvidenceItem
from desktop_app.highlights.highlight_models import Highlight, HighlightColor
from desktop_app.highlights.highlight_repository import HighlightRepository
from desktop_app.transcripts.transcript_models import TranscriptSegment


class HighlightService:
    def __init__(self, repository: HighlightRepository) -> None:
        self.repository = repository

    def highlight_transcript_segment(
        self,
        *,
        project_id: str,
        video_id: str,
        transcript_id: str,
        segment: TranscriptSegment,
        color: HighlightColor,
        note: str = "",
        selected_text: str = "",
    ) -> Highlight:
        text = selected_text.strip() or segment.text
        highlight = Highlight.create(
            project_id=project_id,
            video_id=video_id,
            transcript_id=transcript_id,
            segment_id=segment.id,
            highlighted_text=text,
            color=color,
            note=note,
            timestamp=segment.start_time,
        )
        return self.repository.save(highlight)

    def highlight_evidence(self, item: EvidenceItem, *, color: HighlightColor, note: str = "") -> Highlight:
        highlight = Highlight.create(
            project_id=item.project_id,
            video_id=item.source.video_id,
            transcript_id=item.source.transcript_id,
            chunk_id=item.chunk_id,
            highlighted_text=item.chunk_text,
            color=color,
            note=note,
            timestamp=item.start_time,
        )
        return self.repository.save(highlight)

    def list_project_highlights(self, project_id: str) -> list[Highlight]:
        return self.repository.list_by_project(project_id)

    def delete_highlight(self, highlight_id: str) -> bool:
        return self.repository.delete(highlight_id)
