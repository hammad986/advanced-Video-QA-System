from __future__ import annotations

import json

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop_app.answering.answer_models import AnswerJobState, AnswerResult, AnswerStatus, Citation
from desktop_app.chat.chat_models import ChatJobState, ChatJobStatus, ChatMessage, ChatSearchResult, ChatSession
from desktop_app.widgets.chat_thread_view import ChatThreadView


class ChatQuestionInput(QPlainTextEdit):
    send_requested = Signal()

    def keyPressEvent(self, event: object) -> None:
        key = event.key()  # type: ignore[attr-defined]
        modifiers = event.modifiers()  # type: ignore[attr-defined]
        if key in {Qt.Key.Key_Return, Qt.Key.Key_Enter} and not (modifiers & Qt.KeyboardModifier.ShiftModifier):
            self.send_requested.emit()
            event.accept()  # type: ignore[attr-defined]
            return
        super().keyPressEvent(event)  # type: ignore[arg-type]


class ChatWorkspaceWidget(QGroupBox):
    question_requested = Signal(str, int, float)
    new_chat_requested = Signal()
    session_selected = Signal(str)
    rename_chat_requested = Signal(str, str)
    delete_chat_requested = Signal(str)
    restore_previous_requested = Signal()
    search_requested = Signal(str)
    citation_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__("Research Chat", parent)
        self.thread_view = ChatThreadView()
        self.question_input = ChatQuestionInput()
        self.question_input.setPlaceholderText("Ask a question about the loaded videos")
        self.question_input.setMaximumHeight(56)
        self.answer_output = QPlainTextEdit()
        self.answer_output.setReadOnly(True)
        self.answer_output.setVisible(False)
        self.ask_button = QPushButton("Send")
        self.status_label = QLabel("")
        self.status_label.setVisible(False)

        controls = QHBoxLayout()
        controls.addWidget(self.question_input, 1)
        controls.addWidget(self.ask_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.thread_view, 1)
        layout.addWidget(self.answer_output)
        layout.addWidget(self.status_label)
        layout.addLayout(controls)

        self.ask_button.clicked.connect(self._emit_question)
        self.question_input.send_requested.connect(self._emit_question)
        self.thread_view.message_selected.connect(self._handle_message_selected)
        QTimer.singleShot(0, self.question_input.setFocus)

    def set_sessions(self, sessions: list[ChatSession], active_session_id: str | None = None) -> None:
        _ = sessions, active_session_id

    def set_messages(self, messages: list[ChatMessage]) -> None:
        self.thread_view.set_messages(messages)

    def append_message(self, message: ChatMessage) -> None:
        self.thread_view.append_message(message)
        self.ask_button.setEnabled(True)
        self.status_label.setVisible(False)
        self.question_input.setFocus()

    def set_search_results(self, results: list[ChatSearchResult]) -> None:
        self.thread_view.set_messages([result.message for result in results])

    def set_result(self, result: AnswerResult) -> None:
        self.answer_output.setPlainText(result.answer)
        _ = result
        self.ask_button.setEnabled(True)
        self.status_label.setVisible(False)
        self.question_input.setFocus()

    def apply_state(self, state: AnswerJobState | ChatJobState) -> None:
        running = state.status in {
            AnswerStatus.QUEUED,
            AnswerStatus.RUNNING,
            ChatJobStatus.QUEUED,
            ChatJobStatus.RUNNING,
        }
        self.ask_button.setEnabled(not running)
        self.status_label.setText("Generating answer..." if running else "")
        self.status_label.setVisible(running)
        if not running:
            self.question_input.setFocus()

    def set_error(self, message: str) -> None:
        self.ask_button.setEnabled(True)
        self.status_label.setText(message)
        self.status_label.setVisible(bool(message))
        self.question_input.setFocus()

    def _emit_question(self) -> None:
        question = self.question_input.toPlainText().strip()
        if not question:
            return
        self.question_input.clear()
        self.question_requested.emit(question, 5, 0.0)

    def _handle_message_selected(self, message: object) -> None:
        if isinstance(message, ChatMessage):
            citations = self._parse_citations(message.citations_json)
            if citations:
                self.citation_selected.emit(citations[0])

    def _parse_citations(self, citations_json: str) -> list[Citation]:
        try:
            payload = json.loads(citations_json)
        except json.JSONDecodeError:
            return []
        citations: list[Citation] = []
        for item in payload if isinstance(payload, list) else []:
            if isinstance(item, dict):
                citations.append(
                    Citation(
                        citation_id=int(item.get("citation_id", 0)),
                        source_video=str(item.get("source_video", "")),
                        chunk_id=str(item.get("chunk_id", "")),
                        timestamp_start=float(item.get("timestamp_start", 0.0)),
                        timestamp_end=float(item.get("timestamp_end", 0.0)),
                        confidence=float(item.get("confidence", 0.0)),
                        source_video_id=str(item.get("source_video_id", "")),
                        source_file_path=str(item.get("source_file_path", "")),
                    )
                )
        return citations
