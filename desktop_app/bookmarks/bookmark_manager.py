from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from desktop_app.bookmarks.bookmark_models import Bookmark
from desktop_app.bookmarks.bookmark_service import BookmarkService
from desktop_app.evidence.evidence_models import EvidenceItem
from desktop_app.transcripts.transcript_models import TranscriptSegment


class BookmarkManager(QObject):
    bookmarks_changed = Signal(str)
    bookmark_created = Signal(object)
    bookmark_deleted = Signal(str)

    def __init__(self, service: BookmarkService) -> None:
        super().__init__()
        self.service = service

    def bookmark_evidence(self, item: EvidenceItem, *, title: str, note: str = "") -> Bookmark:
        bookmark = self.service.bookmark_evidence(item, title=title, note=note)
        self.bookmark_created.emit(bookmark)
        self.bookmarks_changed.emit(bookmark.project_id)
        return bookmark

    def bookmark_transcript_segment(
        self,
        *,
        project_id: str,
        video_id: str,
        transcript_id: str,
        segment: TranscriptSegment,
        title: str,
        note: str = "",
    ) -> Bookmark:
        bookmark = self.service.bookmark_transcript_segment(
            project_id=project_id,
            video_id=video_id,
            transcript_id=transcript_id,
            segment=segment,
            title=title,
            note=note,
        )
        self.bookmark_created.emit(bookmark)
        self.bookmarks_changed.emit(bookmark.project_id)
        return bookmark

    def bookmark_video_timestamp(
        self,
        *,
        project_id: str,
        video_id: str,
        timestamp: float,
        title: str,
        note: str = "",
    ) -> Bookmark:
        bookmark = self.service.bookmark_video_timestamp(
            project_id=project_id,
            video_id=video_id,
            timestamp=timestamp,
            title=title,
            note=note,
        )
        self.bookmark_created.emit(bookmark)
        self.bookmarks_changed.emit(bookmark.project_id)
        return bookmark

    def list_project_bookmarks(self, project_id: str) -> list[Bookmark]:
        return self.service.list_project_bookmarks(project_id)

    def delete_bookmark(self, bookmark_id: str) -> bool:
        deleted = self.service.delete_bookmark(bookmark_id)
        if deleted:
            self.bookmark_deleted.emit(bookmark_id)
        return deleted
