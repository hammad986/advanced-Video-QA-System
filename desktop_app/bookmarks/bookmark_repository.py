from __future__ import annotations

from sqlite3 import Row

from desktop_app.bookmarks.bookmark_models import Bookmark, BookmarkType
from desktop_app.database.connection import DatabaseConnection


class BookmarkRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save(self, bookmark: Bookmark) -> Bookmark:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO bookmarks (
                    id, project_id, video_id, chunk_id, transcript_id, segment_id,
                    bookmark_type, title, note, timestamp, source_text,
                    created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title = excluded.title,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (
                    bookmark.id,
                    bookmark.project_id,
                    bookmark.video_id,
                    bookmark.chunk_id,
                    bookmark.transcript_id,
                    bookmark.segment_id,
                    bookmark.bookmark_type.value,
                    bookmark.title,
                    bookmark.note,
                    bookmark.timestamp,
                    bookmark.source_text,
                    bookmark.created_at,
                    bookmark.updated_at,
                ),
            )
        return bookmark

    def list_by_project(self, project_id: str, *, limit: int = 500) -> list[Bookmark]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM bookmarks
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        return [self._row_to_bookmark(row) for row in rows]

    def get(self, bookmark_id: str) -> Bookmark | None:
        with self.connection.connect() as connection:
            row = connection.execute("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,)).fetchone()
        return self._row_to_bookmark(row) if row else None

    def delete(self, bookmark_id: str) -> bool:
        with self.connection.connect() as connection:
            cursor = connection.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
        return cursor.rowcount > 0

    def _row_to_bookmark(self, row: Row) -> Bookmark:
        return Bookmark(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            video_id=str(row["video_id"]),
            chunk_id=str(row["chunk_id"]),
            transcript_id=str(row["transcript_id"]),
            segment_id=str(row["segment_id"]),
            bookmark_type=BookmarkType(str(row["bookmark_type"])),
            title=str(row["title"]),
            note=str(row["note"]),
            timestamp=float(row["timestamp"]),
            source_text=str(row["source_text"]),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )
