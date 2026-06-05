from __future__ import annotations

from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection
from desktop_app.evidence.evidence_models import EvidenceHistoryRecord, EvidenceSource


class EvidenceRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save_history(self, records: list[EvidenceHistoryRecord]) -> None:
        if not records:
            return
        with self.connection.connect() as connection:
            connection.executemany(
                """
                INSERT INTO evidence_history (
                    id, project_id, query, chunk_id, rank,
                    similarity_score, confidence_score, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        record.id,
                        record.project_id,
                        record.query,
                        record.chunk_id,
                        record.rank,
                        record.similarity_score,
                        record.confidence_score,
                        record.created_at,
                    )
                    for record in records
                ],
            )

    def list_history(self, project_id: str, limit: int = 100) -> list[EvidenceHistoryRecord]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM evidence_history
                WHERE project_id = ?
                ORDER BY created_at DESC, rank ASC
                LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        return [self._row_to_history(row) for row in rows]

    def get_sources(self, chunk_ids: list[str]) -> dict[str, EvidenceSource]:
        if not chunk_ids:
            return {}
        placeholders = ", ".join("?" for _ in chunk_ids)
        with self.connection.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT kc.chunk_id, t.id AS transcript_id, v.id AS video_id,
                       v.name AS video_name, v.file_path
                FROM knowledge_chunks kc
                INNER JOIN transcripts t ON t.id = kc.transcript_id
                INNER JOIN videos v ON v.id = t.video_id
                WHERE kc.chunk_id IN ({placeholders})
                """,
                tuple(chunk_ids),
            ).fetchall()
        return {
            str(row["chunk_id"]): EvidenceSource(
                video_id=str(row["video_id"]),
                video_name=str(row["video_name"]),
                file_path=str(row["file_path"]),
                transcript_id=str(row["transcript_id"]),
            )
            for row in rows
        }

    def _row_to_history(self, row: Row) -> EvidenceHistoryRecord:
        return EvidenceHistoryRecord(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            query=str(row["query"]),
            chunk_id=str(row["chunk_id"]),
            rank=int(row["rank"]),
            similarity_score=float(row["similarity_score"]),
            confidence_score=float(row["confidence_score"]),
            created_at=float(row["created_at"]),
        )
