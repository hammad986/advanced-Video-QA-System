from __future__ import annotations

from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection
from desktop_app.retrieval.retrieval_models import RetrievalChunk, RetrievalHistoryRecord


class RetrievalRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save_history(self, record: RetrievalHistoryRecord) -> RetrievalHistoryRecord:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO retrieval_history (
                    id, project_id, query, embedding_model, top_k, duration_ms, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.project_id,
                    record.query,
                    record.embedding_model,
                    record.top_k,
                    record.duration_ms,
                    record.created_at,
                ),
            )
        return record

    def list_history(self, project_id: str, limit: int = 50) -> list[RetrievalHistoryRecord]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM retrieval_history
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        return [self._row_to_history(row) for row in rows]

    def get_chunks(self, chunk_ids: list[str]) -> dict[str, RetrievalChunk]:
        if not chunk_ids:
            return {}
        placeholders = ", ".join("?" for _ in chunk_ids)
        with self.connection.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT chunk_id, transcript_id, start_time, end_time, chunk_text,
                       topic_title, confidence, word_count
                FROM knowledge_chunks
                WHERE chunk_id IN ({placeholders})
                """,
                tuple(chunk_ids),
            ).fetchall()
        return {str(row["chunk_id"]): self._row_to_chunk(row) for row in rows}

    def _row_to_history(self, row: Row) -> RetrievalHistoryRecord:
        return RetrievalHistoryRecord(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            query=str(row["query"]),
            embedding_model=str(row["embedding_model"]),
            top_k=int(row["top_k"]),
            duration_ms=float(row["duration_ms"]),
            created_at=float(row["created_at"]),
        )

    def _row_to_chunk(self, row: Row) -> RetrievalChunk:
        return RetrievalChunk(
            chunk_id=str(row["chunk_id"]),
            transcript_id=str(row["transcript_id"]),
            start_time=float(row["start_time"]),
            end_time=float(row["end_time"]),
            chunk_text=str(row["chunk_text"]),
            topic_title=str(row["topic_title"]),
            confidence=float(row["confidence"]),
            word_count=int(row["word_count"]),
        )
