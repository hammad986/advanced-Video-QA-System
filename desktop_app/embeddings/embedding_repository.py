from __future__ import annotations

from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection
from desktop_app.embeddings.embedding_models import EmbeddingRecord


class EmbeddingRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save_embedding(self, record: EmbeddingRecord) -> None:
        self.replace_embeddings([record])

    def replace_embeddings(self, records: list[EmbeddingRecord]) -> None:
        if not records:
            return
        with self.connection.connect() as connection:
            connection.executemany(
                """
                INSERT INTO embeddings (
                    id, chunk_id, model_name, dimension, embedding_blob, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(chunk_id, model_name) DO UPDATE SET
                    id = excluded.id,
                    dimension = excluded.dimension,
                    embedding_blob = excluded.embedding_blob,
                    created_at = excluded.created_at
                """,
                [
                    (
                        record.id,
                        record.chunk_id,
                        record.model_name,
                        record.dimension,
                        record.embedding_blob,
                        record.created_at,
                    )
                    for record in records
                ],
            )

    def get_by_chunk_and_model(self, chunk_id: str, model_name: str) -> EmbeddingRecord | None:
        with self.connection.connect() as connection:
            row = connection.execute(
                "SELECT * FROM embeddings WHERE chunk_id = ? AND model_name = ?",
                (chunk_id, model_name),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list_by_model(self, model_name: str) -> list[EmbeddingRecord]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM embeddings WHERE model_name = ? ORDER BY created_at ASC",
                (model_name,),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def count_by_model(self, model_name: str) -> int:
        with self.connection.connect() as connection:
            row = connection.execute(
                "SELECT COUNT(*) AS count FROM embeddings WHERE model_name = ?",
                (model_name,),
            ).fetchone()
        return int(row["count"]) if row else 0

    def count_for_chunks(self, chunk_ids: list[str], model_name: str) -> int:
        if not chunk_ids:
            return 0
        placeholders = ", ".join("?" for _ in chunk_ids)
        with self.connection.connect() as connection:
            row = connection.execute(
                f"""
                SELECT COUNT(*) AS count
                FROM embeddings
                WHERE model_name = ? AND chunk_id IN ({placeholders})
                """,
                (model_name, *chunk_ids),
            ).fetchone()
        return int(row["count"]) if row else 0

    def _row_to_record(self, row: Row) -> EmbeddingRecord:
        return EmbeddingRecord(
            id=str(row["id"]),
            chunk_id=str(row["chunk_id"]),
            model_name=str(row["model_name"]),
            dimension=int(row["dimension"]),
            embedding_blob=bytes(row["embedding_blob"]),
            created_at=float(row["created_at"]),
        )
