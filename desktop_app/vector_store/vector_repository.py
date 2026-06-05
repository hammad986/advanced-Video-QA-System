from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection
from desktop_app.embeddings.embedding_models import deserialize_vector


@dataclass(frozen=True)
class ProjectEmbeddingVector:
    chunk_id: str
    vector: list[float]


@dataclass(frozen=True)
class VectorIndexRecord:
    id: str
    project_id: str
    embedding_model: str
    dimension: int
    index_path: str
    created_at: float
    updated_at: float

    @classmethod
    def create(
        cls,
        *,
        project_id: str,
        embedding_model: str,
        dimension: int,
        index_path: str,
    ) -> "VectorIndexRecord":
        now = time.time()
        return cls(
            id=str(uuid.uuid4()),
            project_id=project_id,
            embedding_model=embedding_model,
            dimension=dimension,
            index_path=index_path,
            created_at=now,
            updated_at=now,
        )


class VectorRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save_index(self, record: VectorIndexRecord) -> VectorIndexRecord:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO vector_indexes (
                    id, project_id, embedding_model, dimension, index_path, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    embedding_model = excluded.embedding_model,
                    dimension = excluded.dimension,
                    index_path = excluded.index_path,
                    updated_at = excluded.updated_at
                """,
                (
                    record.id,
                    record.project_id,
                    record.embedding_model,
                    record.dimension,
                    record.index_path,
                    record.created_at,
                    record.updated_at,
                ),
            )
        return record

    def latest_for_project(self, project_id: str, embedding_model: str) -> VectorIndexRecord | None:
        with self.connection.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM vector_indexes
                WHERE project_id = ? AND embedding_model = ?
                ORDER BY updated_at DESC
                LIMIT 1
                """,
                (project_id, embedding_model),
            ).fetchone()
        return self._row_to_record(row) if row else None

    def list_project_embeddings(self, project_id: str, embedding_model: str) -> list[ProjectEmbeddingVector]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                """
                SELECT e.chunk_id, e.embedding_blob
                FROM embeddings e
                INNER JOIN knowledge_chunks kc ON kc.chunk_id = e.chunk_id
                INNER JOIN transcripts t ON t.id = kc.transcript_id
                INNER JOIN videos v ON v.id = t.video_id
                WHERE v.project_id = ? AND e.model_name = ?
                ORDER BY kc.start_time ASC, e.created_at ASC
                """,
                (project_id, embedding_model),
            ).fetchall()
        return [
            ProjectEmbeddingVector(
                chunk_id=str(row["chunk_id"]),
                vector=deserialize_vector(bytes(row["embedding_blob"])),
            )
            for row in rows
        ]

    def _row_to_record(self, row: Row) -> VectorIndexRecord:
        return VectorIndexRecord(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            embedding_model=str(row["embedding_model"]),
            dimension=int(row["dimension"]),
            index_path=str(row["index_path"]),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )
