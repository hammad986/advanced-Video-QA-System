from __future__ import annotations

from sqlite3 import Row

from desktop_app.answering.answer_models import ChatHistoryRecord
from desktop_app.database.connection import DatabaseConnection


class AnswerRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save_chat(self, record: ChatHistoryRecord) -> ChatHistoryRecord:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_history (
                    id, project_id, question, answer, citations_json,
                    provider, duration_ms, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.project_id,
                    record.question,
                    record.answer,
                    record.citations_json,
                    record.provider,
                    record.duration_ms,
                    record.created_at,
                    record.updated_at,
                ),
            )
        return record

    def list_chat_history(self, project_id: str, limit: int = 100) -> list[ChatHistoryRecord]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM chat_history
                WHERE project_id = ?
                ORDER BY created_at DESC
                LIMIT ?
                """,
                (project_id, limit),
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def _row_to_record(self, row: Row) -> ChatHistoryRecord:
        return ChatHistoryRecord(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            question=str(row["question"]),
            answer=str(row["answer"]),
            citations_json=str(row["citations_json"]),
            provider=str(row["provider"]),
            duration_ms=float(row["duration_ms"]),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )
