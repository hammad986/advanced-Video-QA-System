from __future__ import annotations

from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection
from desktop_app.highlights.highlight_models import Highlight, HighlightColor


class HighlightRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save(self, highlight: Highlight) -> Highlight:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO highlights (
                    id, project_id, video_id, transcript_id, segment_id, chunk_id,
                    highlighted_text, color, note, timestamp, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    color = excluded.color,
                    note = excluded.note,
                    updated_at = excluded.updated_at
                """,
                (
                    highlight.id,
                    highlight.project_id,
                    highlight.video_id,
                    highlight.transcript_id,
                    highlight.segment_id,
                    highlight.chunk_id,
                    highlight.highlighted_text,
                    highlight.color.value,
                    highlight.note,
                    highlight.timestamp,
                    highlight.created_at,
                    highlight.updated_at,
                ),
            )
        return highlight

    def list_by_project(self, project_id: str, *, limit: int = 500) -> list[Highlight]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM highlights
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        return [self._row_to_highlight(row) for row in rows]

    def get(self, highlight_id: str) -> Highlight | None:
        with self.connection.connect() as connection:
            row = connection.execute("SELECT * FROM highlights WHERE id = ?", (highlight_id,)).fetchone()
        return self._row_to_highlight(row) if row else None

    def delete(self, highlight_id: str) -> bool:
        with self.connection.connect() as connection:
            cursor = connection.execute("DELETE FROM highlights WHERE id = ?", (highlight_id,))
        return cursor.rowcount > 0

    def _row_to_highlight(self, row: Row) -> Highlight:
        return Highlight(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            video_id=str(row["video_id"]),
            transcript_id=str(row["transcript_id"]),
            segment_id=str(row["segment_id"]),
            chunk_id=str(row["chunk_id"]),
            highlighted_text=str(row["highlighted_text"]),
            color=HighlightColor(str(row["color"])),
            note=str(row["note"]),
            timestamp=float(row["timestamp"]),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )
