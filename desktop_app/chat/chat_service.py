from __future__ import annotations

import json
import time

from desktop_app.answering.answer_service import AnswerService
from desktop_app.chat.chat_models import ChatMessage, ChatSession
from desktop_app.chat.chat_repository import ChatRepository


class ChatService:
    def __init__(self, chat_repository: ChatRepository, answer_service: AnswerService) -> None:
        self.chat_repository = chat_repository
        self.answer_service = answer_service

    def create_session(self, project_id: str, title: str = "New Chat") -> ChatSession:
        return self.chat_repository.create_session(ChatSession.create(project_id=project_id, title=title))

    def ask(
        self,
        *,
        session_id: str,
        project_id: str,
        question: str,
        embedding_selection: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> ChatMessage:
        session = self.chat_repository.get_session(session_id)
        if session is None:
            raise ValueError("Chat session does not exist.")
        if session.project_id != project_id:
            raise ValueError("Chat session belongs to a different project.")
        result = self.answer_service.answer(
            project_id=project_id,
            question=question,
            embedding_selection=embedding_selection,
            top_k=top_k,
            min_similarity=min_similarity,
        )
        message = ChatMessage.create(
            session_id=session_id,
            project_id=project_id,
            question=result.question,
            answer=result.answer,
            citations_json=self.answer_service.citation_builder.to_json(result.citations),
            provider=result.provider,
            provider_model=result.provider_model,
            duration_ms=result.duration_ms,
            token_usage_json=json.dumps(result.token_usage, sort_keys=True),
            citations=result.citations,
            evidence_items=result.evidence_items,
        )
        saved = self.chat_repository.add_message(message)
        if session.title == "New Chat":
            title = self._title_from_question(question)
            self.chat_repository.rename_session(session_id, title, time.time())
        return saved

    def _title_from_question(self, question: str) -> str:
        title = " ".join(question.strip().split())
        if len(title) > 48:
            return f"{title[:45]}..."
        return title or "New Chat"
