from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QPushButton, QVBoxLayout, QWidget

from desktop_app.projects.project_models import ResearchProject


class ProjectSwitcher(QWidget):
    create_requested = Signal()
    open_requested = Signal()
    archive_requested = Signal(str)
    restore_requested = Signal(str)
    delete_requested = Signal(str)
    project_selected = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._projects: list[ResearchProject] = []

        self.project_combo = QComboBox()
        self.project_combo.currentIndexChanged.connect(self._emit_selected_project)

        self.create_button = QPushButton("New")
        self.open_button = QPushButton("Open")
        self.archive_button = QPushButton("Archive")
        self.restore_button = QPushButton("Restore")
        self.delete_button = QPushButton("Delete")

        self.create_button.clicked.connect(self.create_requested.emit)
        self.open_button.clicked.connect(self.open_requested.emit)
        self.archive_button.clicked.connect(self._emit_archive)
        self.restore_button.clicked.connect(self._emit_restore)
        self.delete_button.clicked.connect(self._emit_delete)

        top_row = QHBoxLayout()
        top_row.addWidget(self.project_combo, 1)

        first_row = QHBoxLayout()
        first_row.addWidget(self.create_button)
        first_row.addWidget(self.open_button)

        second_row = QHBoxLayout()
        second_row.addWidget(self.archive_button)
        second_row.addWidget(self.restore_button)
        second_row.addWidget(self.delete_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.setSpacing(6)
        layout.addLayout(top_row)
        layout.addLayout(first_row)
        layout.addLayout(second_row)

    def set_projects(self, projects: list[ResearchProject], active_project_id: str | None = None) -> None:
        self._projects = projects
        self.project_combo.blockSignals(True)
        self.project_combo.clear()
        self.project_combo.addItem("No Project", "")
        for project in projects:
            label = project.name if project.status.value == "active" else f"{project.name} (Archived)"
            self.project_combo.addItem(label, project.id)
        if active_project_id:
            index = self.project_combo.findData(active_project_id)
            if index >= 0:
                self.project_combo.setCurrentIndex(index)
        self.project_combo.blockSignals(False)
        self._update_buttons()

    def current_project_id(self) -> str | None:
        value = self.project_combo.currentData()
        return str(value) if value else None

    def _emit_selected_project(self) -> None:
        project_id = self.current_project_id()
        self._update_buttons()
        if project_id:
            self.project_selected.emit(project_id)

    def _emit_archive(self) -> None:
        project_id = self.current_project_id()
        if project_id:
            self.archive_requested.emit(project_id)

    def _emit_restore(self) -> None:
        project_id = self.current_project_id()
        if project_id:
            self.restore_requested.emit(project_id)

    def _emit_delete(self) -> None:
        project_id = self.current_project_id()
        if project_id:
            self.delete_requested.emit(project_id)

    def _update_buttons(self) -> None:
        has_project = self.current_project_id() is not None
        self.archive_button.setEnabled(has_project)
        self.restore_button.setEnabled(has_project)
        self.delete_button.setEnabled(has_project)

