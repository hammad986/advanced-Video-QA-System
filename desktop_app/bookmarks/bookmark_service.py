from __future__ import annotations

from desktop_app.bookmarks.bookmark_models import Bookmark, BookmarkType
from desktop_app.bookmarks.bookmark_repository import BookmarkRepository
from desktop_app.evidence.evidence_models import EvidenceItem
from desktop_app.transcripts.transcript_models import TranscriptSegment


class BookmarkService:
    def __init__(self, repository: BookmarkRepository) -> None:
        self.repository = repository

    def bookmark_evidence(self, item: EvidenceItem, *, title: str, note: str = "") -> Bookmark:
        bookmark = Bookmark.create(
            project_id=item.project_id,
            bookmark_type=BookmarkType.EVIDENCE,
            title=title or item.topic_title,
            note=note,
            video_id=item.source.video_id,
            chunk_id=item.chunk_id,
            transcript_id=item.source.transcript_id,
            timestamp=item.start_time,
            source_text=item.chunk_text,
        )
        return self.repository.save(bookmark)

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
        bookmark = Bookmark.create(
            project_id=project_id,
            bookmark_type=BookmarkType.TRANSCRIPT_SEGMENT,
            title=title,
            note=note,
            video_id=video_id,
            transcript_id=transcript_id,
            segment_id=segment.id,
            timestamp=segment.start_time,
            source_text=segment.text,
        )
        return self.repository.save(bookmark)

    def bookmark_video_timestamp(
        self,
        *,
        project_id: str,
        video_id: str,
        timestamp: float,
        title: str,
        note: str = "",
    ) -> Bookmark:
        bookmark = Bookmark.create(
            project_id=project_id,
            bookmark_type=BookmarkType.VIDEO_TIMESTAMP,
            title=title,
            note=note,
            video_id=video_id,
            timestamp=timestamp,
        )
        return self.repository.save(bookmark)

    def list_project_bookmarks(self, project_id: str) -> list[Bookmark]:
        return self.repository.list_by_project(project_id)

    def delete_bookmark(self, bookmark_id: str) -> bool:
        return self.repository.delete(bookmark_id)
