from __future__ import annotations

from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection
from desktop_app.videos.video_model import VideoRecord


class VideoRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save(self, video: VideoRecord) -> VideoRecord:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO videos (
                    id, project_id, name, file_path, file_size, duration, fps,
                    width, height, thumbnail_path, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name = excluded.name,
                    file_path = excluded.file_path,
                    file_size = excluded.file_size,
                    duration = excluded.duration,
                    fps = excluded.fps,
                    width = excluded.width,
                    height = excluded.height,
                    thumbnail_path = excluded.thumbnail_path,
                    updated_at = excluded.updated_at
                """,
                (
                    video.id,
                    video.project_id,
                    video.name,
                    video.file_path,
                    video.file_size,
                    video.duration,
                    video.fps,
                    video.width,
                    video.height,
                    video.thumbnail_path,
                    video.created_at,
                    video.updated_at,
                ),
            )
        return video

    def list_by_project(self, project_id: str, *, search: str = "") -> list[VideoRecord]:
        pattern = f"%{search.strip()}%"
        sql = "SELECT * FROM videos WHERE project_id = ?"
        params: tuple[object, ...] = (project_id,)
        if search.strip():
            sql += " AND name LIKE ?"
            params = (project_id, pattern)
        sql += " ORDER BY updated_at DESC, name ASC"
        with self.connection.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._row_to_video(row) for row in rows]

    def get(self, video_id: str) -> VideoRecord | None:
        with self.connection.connect() as connection:
            row = connection.execute("SELECT * FROM videos WHERE id = ?", (video_id,)).fetchone()
        return self._row_to_video(row) if row is not None else None

    def find_by_project_path(self, project_id: str, file_path: str) -> VideoRecord | None:
        with self.connection.connect() as connection:
            row = connection.execute(
                "SELECT * FROM videos WHERE project_id = ? AND file_path = ?",
                (project_id, file_path),
            ).fetchone()
        return self._row_to_video(row) if row is not None else None

    def delete(self, video_id: str) -> bool:
        with self.connection.connect() as connection:
            cursor = connection.execute("DELETE FROM videos WHERE id = ?", (video_id,))
        return cursor.rowcount > 0

    def _row_to_video(self, row: Row) -> VideoRecord:
        return VideoRecord(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            name=str(row["name"]),
            file_path=str(row["file_path"]),
            file_size=int(row["file_size"]),
            duration=float(row["duration"]),
            fps=float(row["fps"]),
            width=int(row["width"]),
            height=int(row["height"]),
            thumbnail_path=str(row["thumbnail_path"] or ""),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )

