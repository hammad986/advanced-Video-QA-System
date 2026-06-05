from __future__ import annotations

import time

from PySide6.QtCore import QObject, Signal

from desktop_app.chat.chat_models import ChatSearchResult, ChatSession
from desktop_app.chat.chat_repository import ChatRepository


class ChatSessionManager(QObject):
    sessions_changed = Signal(object)
    active_session_changed = Signal(object)

    def __init__(self, chat_repository: ChatRepository) -> None:
        super().__init__()
        self.chat_repository = chat_repository
        self.active_session_id: str | None = None

    def create_session(self, project_id: str, title: str = "New Chat") -> ChatSession:
        session = self.chat_repository.create_session(ChatSession.create(project_id=project_id, title=title))
        self.active_session_id = session.id
        self.sessions_changed.emit(project_id)
        self.active_session_changed.emit(session)
        return session

    def ensure_active_session(self, project_id: str) -> ChatSession:
        if self.active_session_id is not None:
            session = self.chat_repository.get_session(self.active_session_id)
            if session is not None and session.project_id == project_id and session.deleted_at is None:
                return session
        sessions = self.chat_repository.list_sessions(project_id)
        if sessions:
            self.active_session_id = sessions[0].id
            self.active_session_changed.emit(sessions[0])
            return sessions[0]
        return self.create_session(project_id)

    def set_active_session(self, session_id: str) -> ChatSession | None:
        session = self.chat_repository.get_session(session_id)
        if session is None:
            return None
        self.active_session_id = session.id
        self.active_session_changed.emit(session)
        return session

    def list_sessions(self, project_id: str, *, include_deleted: bool = False) -> list[ChatSession]:
        return self.chat_repository.list_sessions(project_id, include_deleted=include_deleted)

    def rename_session(self, session_id: str, title: str) -> ChatSession | None:
        session = self.chat_repository.rename_session(session_id, title.strip() or "Untitled Chat", time.time())
        if session is not None:
            self.sessions_changed.emit(session.project_id)
        return session

    def delete_session(self, session_id: str) -> ChatSession | None:
        session = self.chat_repository.mark_deleted(session_id, time.time())
        if session is not None:
            if self.active_session_id == session_id:
                self.active_session_id = None
            self.sessions_changed.emit(session.project_id)
        return session

    def restore_session(self, session_id: str) -> ChatSession | None:
        session = self.chat_repository.restore_session(session_id, time.time())
        if session is not None:
            self.active_session_id = session.id
            self.sessions_changed.emit(session.project_id)
            self.active_session_changed.emit(session)
        return session

    def search(self, project_id: str, query: str) -> list[ChatSearchResult]:
        return self.chat_repository.search(project_id, query)
