from __future__ import annotations

import json
from datetime import datetime

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import QListView, QVBoxLayout, QWidget

from desktop_app.answering.answer_models import Citation
from desktop_app.chat.chat_models import ChatMessage


class ChatThreadListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[ChatMessage] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.messages)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self.messages):
            return None
        message = self.messages[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            created = datetime.fromtimestamp(message.created_at).strftime("%Y-%m-%d %H:%M")
            model = f" · {message.provider_model}" if message.provider_model else ""
            tokens = self._token_summary(message.token_usage_json)
            token_label = f" · {tokens}" if tokens else ""
            citation_count = len(self._parse_citations(message.citations_json))
            return (
                f"You: {message.question}\n\n"
                f"Assistant: {message.answer}\n\n"
                f"{created} · {message.provider}{model} · {message.duration_ms:.1f} ms"
                f"{token_label} · {citation_count} citations"
            )
        if role == Qt.ItemDataRole.UserRole:
            return message
        return None

    def set_messages(self, messages: list[ChatMessage]) -> None:
        self.beginResetModel()
        self.messages = messages
        self.endResetModel()

    def append_message(self, message: ChatMessage) -> None:
        row = len(self.messages)
        self.beginInsertRows(QModelIndex(), row, row)
        self.messages.append(message)
        self.endInsertRows()

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

    def _token_summary(self, token_usage_json: str) -> str:
        try:
            payload = json.loads(token_usage_json)
        except json.JSONDecodeError:
            return ""
        total = payload.get("total_tokens") if isinstance(payload, dict) else None
        return f"{total} tokens" if isinstance(total, int) else ""


class ChatThreadView(QWidget):
    message_selected = Signal(object)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model = ChatThreadListModel()
        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.setUniformItemSizes(False)
        self.list_view.clicked.connect(self._emit_selected)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.list_view)

    def set_messages(self, messages: list[ChatMessage]) -> None:
        self.model.set_messages(messages)

    def append_message(self, message: ChatMessage) -> None:
        self.model.append_message(message)
        self.list_view.scrollToBottom()

    def _emit_selected(self, index: QModelIndex) -> None:
        message = self.model.data(index, Qt.ItemDataRole.UserRole)
        if isinstance(message, ChatMessage):
            self.message_selected.emit(message)
