from __future__ import annotations

from sqlite3 import Row

from desktop_app.answering.answer_models import Citation
from desktop_app.chat.chat_models import ChatMessage, ChatSearchResult, ChatSession, ChatSessionStatus
from desktop_app.database.connection import DatabaseConnection


class ChatRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def create_session(self, session: ChatSession) -> ChatSession:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_sessions (
                    id, project_id, title, status, created_at,
                    updated_at, last_message_at, deleted_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    session.id,
                    session.project_id,
                    session.title,
                    session.status.value,
                    session.created_at,
                    session.updated_at,
                    session.last_message_at,
                    session.deleted_at,
                ),
            )
        return session

    def get_session(self, session_id: str) -> ChatSession | None:
        with self.connection.connect() as connection:
            row = connection.execute("SELECT * FROM chat_sessions WHERE id = ?", (session_id,)).fetchone()
        return self._row_to_session(row) if row else None

    def list_sessions(self, project_id: str, *, include_deleted: bool = False) -> list[ChatSession]:
        status_filter = "" if include_deleted else "AND status = 'active'"
        with self.connection.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT * FROM chat_sessions
                WHERE project_id = ? {status_filter}
                ORDER BY COALESCE(last_message_at, updated_at) DESC
                """,
                (project_id,),
            ).fetchall()
        return [self._row_to_session(row) for row in rows]

    def rename_session(self, session_id: str, title: str, updated_at: float) -> ChatSession | None:
        with self.connection.connect() as connection:
            connection.execute(
                "UPDATE chat_sessions SET title = ?, updated_at = ? WHERE id = ?",
                (title, updated_at, session_id),
            )
        return self.get_session(session_id)

    def mark_deleted(self, session_id: str, deleted_at: float) -> ChatSession | None:
        with self.connection.connect() as connection:
            connection.execute(
                """
                UPDATE chat_sessions
                SET status = ?, deleted_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (ChatSessionStatus.DELETED.value, deleted_at, deleted_at, session_id),
            )
        return self.get_session(session_id)

    def restore_session(self, session_id: str, updated_at: float) -> ChatSession | None:
        with self.connection.connect() as connection:
            connection.execute(
                """
                UPDATE chat_sessions
                SET status = ?, deleted_at = NULL, updated_at = ?
                WHERE id = ?
                """,
                (ChatSessionStatus.ACTIVE.value, updated_at, session_id),
            )
        return self.get_session(session_id)

    def add_message(self, message: ChatMessage) -> ChatMessage:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_messages (
                    id, session_id, project_id, question, answer, citations_json,
                    provider, provider_model, duration_ms, token_usage_json, created_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    message.id,
                    message.session_id,
                    message.project_id,
                    message.question,
                    message.answer,
                    message.citations_json,
                    message.provider,
                    message.provider_model,
                    message.duration_ms,
                    message.token_usage_json,
                    message.created_at,
                ),
            )
            connection.execute(
                """
                UPDATE chat_sessions
                SET last_message_at = ?, updated_at = ?
                WHERE id = ?
                """,
                (message.created_at, message.created_at, message.session_id),
            )
        return message

    def list_messages(self, session_id: str) -> list[ChatMessage]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM chat_messages WHERE session_id = ? ORDER BY created_at ASC",
                (session_id,),
            ).fetchall()
        return [self._row_to_message(row) for row in rows]

    def search(self, project_id: str, query: str, *, limit: int = 100) -> list[ChatSearchResult]:
        pattern = f"%{query}%"
        with self.connection.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    s.id AS s_id, s.project_id AS s_project_id, s.title AS s_title,
                    s.status AS s_status, s.created_at AS s_created_at,
                    s.updated_at AS s_updated_at, s.last_message_at AS s_last_message_at,
                    s.deleted_at AS s_deleted_at,
                    m.id AS m_id, m.session_id AS m_session_id, m.project_id AS m_project_id,
                    m.question AS m_question, m.answer AS m_answer,
                    m.citations_json AS m_citations_json, m.provider AS m_provider,
                    m.provider_model AS m_provider_model, m.duration_ms AS m_duration_ms,
                    m.token_usage_json AS m_token_usage_json, m.created_at AS m_created_at
                FROM chat_messages m
                JOIN chat_sessions s ON s.id = m.session_id
                WHERE m.project_id = ?
                  AND s.status = 'active'
                  AND (m.question LIKE ? OR m.answer LIKE ? OR m.citations_json LIKE ?)
                ORDER BY m.created_at DESC
                LIMIT ?
                """,
                (project_id, pattern, pattern, pattern, limit),
            ).fetchall()
        return [self._row_to_search_result(row) for row in rows]

    def _row_to_session(self, row: Row) -> ChatSession:
        return ChatSession(
            id=str(row["id"]),
            project_id=str(row["project_id"]),
            title=str(row["title"]),
            status=ChatSessionStatus(str(row["status"])),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
            last_message_at=None if row["last_message_at"] is None else float(row["last_message_at"]),
            deleted_at=None if row["deleted_at"] is None else float(row["deleted_at"]),
        )

    def _row_to_message(self, row: Row, *, citations: list[Citation] | None = None) -> ChatMessage:
        return ChatMessage(
            id=str(row["id"]),
            session_id=str(row["session_id"]),
            project_id=str(row["project_id"]),
            question=str(row["question"]),
            answer=str(row["answer"]),
            citations_json=str(row["citations_json"]),
            provider=str(row["provider"]),
            provider_model=str(row["provider_model"]),
            duration_ms=float(row["duration_ms"]),
            token_usage_json=str(row["token_usage_json"]),
            created_at=float(row["created_at"]),
            citations=citations or [],
        )

    def _row_to_search_result(self, row: Row) -> ChatSearchResult:
        session = ChatSession(
            id=str(row["s_id"]),
            project_id=str(row["s_project_id"]),
            title=str(row["s_title"]),
            status=ChatSessionStatus(str(row["s_status"])),
            created_at=float(row["s_created_at"]),
            updated_at=float(row["s_updated_at"]),
            last_message_at=None if row["s_last_message_at"] is None else float(row["s_last_message_at"]),
            deleted_at=None if row["s_deleted_at"] is None else float(row["s_deleted_at"]),
        )
        message = ChatMessage(
            id=str(row["m_id"]),
            session_id=str(row["m_session_id"]),
            project_id=str(row["m_project_id"]),
            question=str(row["m_question"]),
            answer=str(row["m_answer"]),
            citations_json=str(row["m_citations_json"]),
            provider=str(row["m_provider"]),
            provider_model=str(row["m_provider_model"]),
            duration_ms=float(row["m_duration_ms"]),
            token_usage_json=str(row["m_token_usage_json"]),
            created_at=float(row["m_created_at"]),
        )
        return ChatSearchResult(session=session, message=message)
