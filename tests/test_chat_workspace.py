from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QTextCursor
from PySide6.QtTest import QTest

from desktop_app.answering.answer_repository import AnswerRepository
from desktop_app.answering.answer_service import AnswerService, ProviderGeneration
from desktop_app.chat.chat_repository import ChatRepository
from desktop_app.chat.chat_service import ChatService
from desktop_app.chat.chat_session_manager import ChatSessionManager
from desktop_app.database.database_manager import DatabaseManager
from desktop_app.evidence.evidence_models import EvidenceItem, EvidenceResult, EvidenceSource
from desktop_app.projects.project_repository import ProjectRepository
from desktop_app.projects.project_service import ProjectService
from desktop_app.widgets.chat_workspace import ChatWorkspaceWidget


class FakeEvidenceService:
    def generate(self, *, project_id, query, embedding_selection, top_k=5, min_similarity=0.0):
        return EvidenceResult(project_id=project_id, query=query, duration_ms=8.0, items=[_evidence_item()])


class FakeProviderExecutor:
    def generate(self, prompt: str) -> ProviderGeneration:
        return ProviderGeneration(
            provider="fake",
            text="The lecture describes unsupervised learning with clustering examples [1].",
            model="fake-model",
            token_usage={"prompt_tokens": 10, "completion_tokens": 12, "total_tokens": 22},
        )


def _evidence_item() -> EvidenceItem:
    return EvidenceItem.create(
        project_id="project",
        query="What is clustering?",
        chunk_id="chunk-chat-1",
        retrieval_rank=1,
        source=EvidenceSource(
            video_id="video-chat-1",
            video_name="lecture.mp4",
            file_path="D:/videos/lecture.mp4",
            transcript_id="transcript-chat-1",
        ),
        topic_title="Clustering",
        start_time=10.0,
        end_time=20.0,
        similarity_score=0.93,
        confidence_score=0.91,
        chunk_text="Clustering groups similar examples without output labels.",
    )


def _services(tmp_path):
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    project = ProjectService(ProjectRepository(database.connection)).create_project(
        name="Chat Project",
        root_path=str(tmp_path / "project"),
    )
    chat_repository = ChatRepository(database.connection)
    answer_service = AnswerService(
        AnswerRepository(database.connection),
        FakeEvidenceService(),
        FakeProviderExecutor(),
    )
    return project, chat_repository, ChatService(chat_repository, answer_service)


def test_chat_service_persists_session_message_and_provider_metadata(tmp_path) -> None:
    project, repository, service = _services(tmp_path)
    session = service.create_session(project.id)

    message = service.ask(
        session_id=session.id,
        project_id=project.id,
        question="What is clustering?",
        embedding_selection="small",
    )
    messages = repository.list_messages(session.id)

    assert message.session_id == session.id
    assert message.provider == "fake"
    assert message.provider_model == "fake-model"
    assert "total_tokens" in message.token_usage_json
    assert "source_file_path" in message.citations_json
    assert message.evidence_items[0].chunk_id == "chunk-chat-1"
    assert messages[0].question == "What is clustering?"


def test_chat_session_manager_rename_delete_restore_and_search(tmp_path) -> None:
    project, repository, service = _services(tmp_path)
    manager = ChatSessionManager(repository)
    session = service.create_session(project.id)
    service.ask(session_id=session.id, project_id=project.id, question="What is clustering?", embedding_selection="small")

    renamed = manager.rename_session(session.id, "Lecture Questions")
    deleted = manager.delete_session(session.id)
    active_after_delete = manager.list_sessions(project.id)
    restored = manager.restore_session(session.id)
    matches = manager.search(project.id, "clustering")

    assert renamed is not None and renamed.title == "Lecture Questions"
    assert deleted is not None and deleted.deleted_at is not None
    assert active_after_delete == []
    assert restored is not None and restored.deleted_at is None
    assert matches and matches[0].session.id == session.id


def test_chat_workspace_emits_question_and_message_citation_events(qapp) -> None:
    widget = ChatWorkspaceWidget()
    emitted_questions = []
    emitted_citations = []
    widget.question_requested.connect(lambda question, top_k, threshold: emitted_questions.append((question, top_k, threshold)))
    widget.citation_selected.connect(lambda citation: emitted_citations.append(citation))

    widget.question_input.setPlainText("What is clustering?")
    widget.ask_button.click()
    message = _message_for_widget()
    widget.append_message(message)
    widget._handle_message_selected(message)

    assert emitted_questions == [("What is clustering?", 5, 0.0)]
    assert emitted_citations[0].chunk_id == "chunk-chat-1"


def test_chat_workspace_contains_only_question_ask_and_conversation(qapp) -> None:
    widget = ChatWorkspaceWidget()
    visible_text = []
    for child in widget.findChildren(object):
        text_getter = getattr(child, "text", None)
        if callable(text_getter):
            visible_text.append(str(text_getter()))

    assert widget.question_input is not None
    assert widget.ask_button.text() == "Send"
    assert widget.thread_view is not None
    assert "Top K" not in visible_text
    assert "Min Score" not in visible_text
    assert "Citations" not in visible_text
    assert "Chats" not in visible_text


def test_chat_workspace_enter_sends_and_shift_enter_inserts_new_line(qapp) -> None:
    widget = ChatWorkspaceWidget()
    emitted_questions = []
    widget.question_requested.connect(lambda question, top_k, threshold: emitted_questions.append((question, top_k, threshold)))

    widget.question_input.setPlainText("Line one")
    widget.question_input.moveCursor(QTextCursor.MoveOperation.End)
    widget.question_input.setFocus()
    QTest.keyClick(widget.question_input, Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier)
    assert widget.question_input.toPlainText() == "Line one\n"

    widget.question_input.setPlainText("What is weighted sum?")
    QTest.keyClick(widget.question_input, Qt.Key.Key_Return)

    assert emitted_questions == [("What is weighted sum?", 5, 0.0)]
    assert widget.question_input.toPlainText() == ""


def test_chat_workspace_disables_send_and_shows_loading(qapp) -> None:
    from desktop_app.chat.chat_models import ChatJobState, ChatJobStatus

    widget = ChatWorkspaceWidget()
    state = ChatJobState(
        job_id="chat-1",
        session_id="session",
        project_id="project",
        question="What is weighted sum?",
        status=ChatJobStatus.RUNNING,
        progress_percent=20,
    )

    widget.apply_state(state)

    assert widget.ask_button.isEnabled() is False
    assert widget.status_label.isHidden() is False
    assert widget.status_label.text() == "Generating answer..."


def _message_for_widget():
    from desktop_app.chat.chat_models import ChatMessage
    from desktop_app.answering.citation_builder import CitationBuilder

    citations = CitationBuilder().build([_evidence_item()])
    return ChatMessage.create(
        session_id="session",
        project_id="project",
        question="What is clustering?",
        answer="Clustering groups similar examples [1].",
        citations_json=CitationBuilder().to_json(citations),
        provider="fake",
        provider_model="fake-model",
        duration_ms=12.0,
        token_usage_json='{"total_tokens": 22}',
        citations=citations,
    )
