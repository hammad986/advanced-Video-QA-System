from __future__ import annotations

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListView,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop_app.chat.chat_models import ChatSession


class ChatSessionListModel(QAbstractListModel):
    def __init__(self) -> None:
        super().__init__()
        self.sessions: list[ChatSession] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self.sessions)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> object:
        if not index.isValid() or not 0 <= index.row() < len(self.sessions):
            return None
        session = self.sessions[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            return session.title
        if role == Qt.ItemDataRole.UserRole:
            return session.id
        return None

    def set_sessions(self, sessions: list[ChatSession]) -> None:
        self.beginResetModel()
        self.sessions = sessions
        self.endResetModel()


class ChatSidebarWidget(QWidget):
    new_chat_requested = Signal()
    session_selected = Signal(str)
    rename_chat_requested = Signal(str, str)
    delete_chat_requested = Signal(str)
    restore_previous_requested = Signal()
    search_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.title_label = QLabel("Chats")
        self.new_button = QPushButton("New")
        self.rename_button = QPushButton("Rename")
        self.delete_button = QPushButton("Delete")
        self.restore_button = QPushButton("Restore Previous")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search chats")
        self.status_label = QLabel("No chat sessions")

        self.model = ChatSessionListModel()
        self.session_view = QListView()
        self.session_view.setModel(self.model)

        action_row = QHBoxLayout()
        action_row.addWidget(self.new_button)
        action_row.addWidget(self.rename_button)
        action_row.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        layout.addWidget(self.title_label)
        layout.addLayout(action_row)
        layout.addWidget(self.restore_button)
        layout.addWidget(self.search_input)
        layout.addWidget(self.session_view, 1)
        layout.addWidget(self.status_label)

        self.new_button.clicked.connect(self.new_chat_requested)
        self.rename_button.clicked.connect(self._rename_selected)
        self.delete_button.clicked.connect(self._delete_selected)
        self.restore_button.clicked.connect(self.restore_previous_requested)
        self.search_input.textChanged.connect(self.search_requested)
        self.session_view.clicked.connect(self._select_session)
        self._update_actions()

    def set_sessions(self, sessions: list[ChatSession], active_session_id: str | None = None) -> None:
        self.model.set_sessions(sessions)
        if active_session_id:
            for row, session in enumerate(sessions):
                if session.id == active_session_id:
                    self.session_view.setCurrentIndex(self.model.index(row))
                    break
        self.status_label.setText(f"{len(sessions):,} chat sessions")
        self._update_actions()

    def set_search_status(self, count: int) -> None:
        self.status_label.setText(f"{count:,} search matches")

    def selected_session_id(self) -> str | None:
        index = self.session_view.currentIndex()
        value = self.model.data(index, Qt.ItemDataRole.UserRole)
        return str(value) if value else None

    def _select_session(self, index: QModelIndex) -> None:
        value = self.model.data(index, Qt.ItemDataRole.UserRole)
        if value:
            self.session_selected.emit(str(value))
        self._update_actions()

    def _rename_selected(self) -> None:
        session_id = self.selected_session_id()
        if not session_id:
            return
        title, accepted = QInputDialog.getText(self, "Rename Chat", "Chat title:")
        if accepted and title.strip():
            self.rename_chat_requested.emit(session_id, title.strip())

    def _delete_selected(self) -> None:
        session_id = self.selected_session_id()
        if session_id:
            self.delete_chat_requested.emit(session_id)

    def _update_actions(self) -> None:
        has_selection = self.selected_session_id() is not None
        self.rename_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)
