from __future__ import annotations

from sqlite3 import Row

from desktop_app.compare.compare_models import CompareSessionRecord, CompareTopic
from desktop_app.database.connection import DatabaseConnection
from desktop_app.videos.video_model import VideoRecord


class CompareRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save_session(self, record: CompareSessionRecord) -> CompareSessionRecord:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO compare_sessions (
                    id, project_id, session_name, videos_json,
                    query, result_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.project_id,
                    record.session_name,
                    record.videos_json,
                    record.query,
                    record.result_json,
                    record.created_at,
                ),
            )
        return record

    def list_sessions(self, project_id: str, limit: int = 100) -> list[CompareSessionRecord]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM compare_sessions
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def get_session(self, session_id: str) -> CompareSessionRecord | None:
        with self.connection.connect() as connection:
            row = connection.execute(
                "SELECT * FROM compare_sessions WHERE id = ?",
                (session_id,),
            ).fetchone()
        return self._row_to_session(row) if row else None

    def list_videos(self, project_id: str) -> list[VideoRecord]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM videos WHERE project_id = ? ORDER BY name ASC",
                (project_id,),
            ).fetchall()
        return [self._row_to_video(row) for row in rows]

    def get_videos(self, video_ids: list[str]) -> list[VideoRecord]:
        if not video_ids:
            return []
        placeholders = ", ".join("?" for _ in video_ids)
        with self.connection.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM videos WHERE id IN ({placeholders})",
                tuple(video_ids),
            ).fetchall()
        videos = [self._row_to_video(row) for row in rows]
        order = {video_id: index for index, video_id in enumerate(video_ids)}
        return sorted(videos, key=lambda video: order.get(video.id, len(order)))

    def list_topics_by_video(self, video_ids: list[str]) -> dict[str, list[CompareTopic]]:
        if not video_ids:
            return {}
        placeholders = ", ".join("?" for _ in video_ids)
        with self.connection.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT v.id AS video_id, v.name AS video_name,
                       kc.topic_title, kc.chunk_id, kc.chunk_text,
                       kc.start_time, kc.end_time, kc.confidence
                FROM knowledge_chunks kc
                INNER JOIN transcripts t ON t.id = kc.transcript_id
                INNER JOIN videos v ON v.id = t.video_id
                WHERE v.id IN ({placeholders})
                ORDER BY v.name ASC, kc.start_time ASC
                """,
                tuple(video_ids),
            ).fetchall()
        topics: dict[str, list[CompareTopic]] = {video_id: [] for video_id in video_ids}
        for row in rows:
            topic = CompareTopic(
                video_id=str(row["video_id"]),
                video_name=str(row["video_name"]),
                topic_title=str(row["topic_title"]),
                chunk_id=str(row["chunk_id"]),
                chunk_text=str(row["chunk_text"]),
                start_time=float(row["start_time"]),
                end_time=float(row["end_time"]),
                confidence=float(row["confidence"]),
            )
            topics.setdefault(topic.video_id, []).append(topic)
        return topics

    def _row_to_session(self, row: Row) -> CompareSessionRecord:
        return CompareSessionRecord(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            session_name=str(row["session_name"]),
            videos_json=str(row["videos_json"]),
            query=str(row["query"]),
            result_json=str(row["result_json"]),
            created_at=float(row["created_at"]),
        )

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
