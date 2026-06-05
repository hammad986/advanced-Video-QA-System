from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from desktop_app.evidence.evidence_models import EvidenceItem
from desktop_app.highlights.highlight_models import Highlight, HighlightColor
from desktop_app.highlights.highlight_service import HighlightService
from desktop_app.transcripts.transcript_models import TranscriptSegment


class HighlightManager(QObject):
    highlights_changed = Signal(str)
    highlight_created = Signal(object)
    highlight_deleted = Signal(str)

    def __init__(self, service: HighlightService) -> None:
        super().__init__()
        self.service = service

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
        highlight = self.service.highlight_transcript_segment(
            project_id=project_id,
            video_id=video_id,
            transcript_id=transcript_id,
            segment=segment,
            color=color,
            note=note,
            selected_text=selected_text,
        )
        self.highlight_created.emit(highlight)
        self.highlights_changed.emit(highlight.project_id)
        return highlight

    def highlight_evidence(self, item: EvidenceItem, *, color: HighlightColor, note: str = "") -> Highlight:
        highlight = self.service.highlight_evidence(item, color=color, note=note)
        self.highlight_created.emit(highlight)
        self.highlights_changed.emit(highlight.project_id)
        return highlight

    def list_project_highlights(self, project_id: str) -> list[Highlight]:
        return self.service.list_project_highlights(project_id)

    def delete_highlight(self, highlight_id: str) -> bool:
        deleted = self.service.delete_highlight(highlight_id)
        if deleted:
            self.highlight_deleted.emit(highlight_id)
        return deleted
