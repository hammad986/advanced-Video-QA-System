from __future__ import annotations

from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection
from desktop_app.knowledge.knowledge_models import ChunkTopic, KnowledgeChunk


class KnowledgeRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def replace_chunks(self, transcript_id: str, chunks: list[KnowledgeChunk], topics: list[ChunkTopic]) -> None:
        with self.connection.connect() as connection:
            old_rows = connection.execute(
                "SELECT chunk_id FROM knowledge_chunks WHERE transcript_id = ?",
                (transcript_id,),
            ).fetchall()
            old_ids = [str(row["chunk_id"]) for row in old_rows]
            if old_ids:
                connection.executemany("DELETE FROM chunk_topics WHERE chunk_id = ?", [(chunk_id,) for chunk_id in old_ids])
            connection.execute("DELETE FROM knowledge_chunks WHERE transcript_id = ?", (transcript_id,))
            connection.executemany(
                """
                INSERT INTO knowledge_chunks (
                    chunk_id, transcript_id, start_time, end_time, chunk_text,
                    topic_title, confidence, word_count, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        chunk.chunk_id,
                        chunk.transcript_id,
                        chunk.start_time,
                        chunk.end_time,
                        chunk.chunk_text,
                        chunk.topic_title,
                        chunk.confidence,
                        chunk.word_count,
                        chunk.created_at,
                    )
                    for chunk in chunks
                ],
            )
            connection.executemany(
                """
                INSERT INTO chunk_topics (id, chunk_id, topic_title, confidence)
                VALUES (?, ?, ?, ?)
                """,
                [(topic.id, topic.chunk_id, topic.topic_title, topic.confidence) for topic in topics],
            )

    def list_chunks(self, transcript_id: str) -> list[KnowledgeChunk]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM knowledge_chunks WHERE transcript_id = ? ORDER BY start_time ASC",
                (transcript_id,),
            ).fetchall()
        return [self._row_to_chunk(row) for row in rows]

    def list_topics(self, chunk_id: str) -> list[ChunkTopic]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM chunk_topics WHERE chunk_id = ? ORDER BY confidence DESC",
                (chunk_id,),
            ).fetchall()
        return [self._row_to_topic(row) for row in rows]

    def _row_to_chunk(self, row: Row) -> KnowledgeChunk:
        return KnowledgeChunk(
            chunk_id=str(row["chunk_id"]),
            transcript_id=str(row["transcript_id"]),
            start_time=float(row["start_time"]),
            end_time=float(row["end_time"]),
            chunk_text=str(row["chunk_text"]),
            topic_title=str(row["topic_title"]),
            confidence=float(row["confidence"]),
            word_count=int(row["word_count"]),
            created_at=float(row["created_at"]),
        )

    def _row_to_topic(self, row: Row) -> ChunkTopic:
        return ChunkTopic(
            id=str(row["id"]),
            chunk_id=str(row["chunk_id"]),
            topic_title=str(row["topic_title"]),
            confidence=float(row["confidence"]),
        )

