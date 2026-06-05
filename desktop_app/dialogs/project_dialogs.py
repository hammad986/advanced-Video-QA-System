from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from desktop_app.projects.project_models import ResearchProject


class CreateProjectDialog(QDialog):
    def __init__(self, default_root: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Create Project")
        self.default_root = default_root

        self.name_input = QLineEdit()
        self.description_input = QTextEdit()
        self.description_input.setFixedHeight(80)
        self.root_input = QLineEdit(str(default_root))
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self._browse)

        root_row = QHBoxLayout()
        root_row.addWidget(self.root_input, 1)
        root_row.addWidget(browse_button)

        form = QFormLayout()
        form.addRow("Name", self.name_input)
        form.addRow("Description", self.description_input)
        form.addRow("Root Folder", root_row)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self._accept_if_valid)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def project_values(self) -> tuple[str, str, str]:
        return (
            self.name_input.text().strip(),
            self.description_input.toPlainText().strip(),
            self.root_input.text().strip(),
        )

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(self, "Choose Project Root", self.root_input.text())
        if selected:
            self.root_input.setText(selected)

    def _accept_if_valid(self) -> None:
        name, _, root_path = self.project_values()
        if not name:
            QMessageBox.warning(self, "Project Name Required", "Enter a project name.")
            return
        if not root_path:
            QMessageBox.warning(self, "Project Folder Required", "Choose a project folder.")
            return
        self.accept()


class OpenProjectDialog(QDialog):
    def __init__(self, projects: list[ResearchProject], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Open Project")
        self.projects = projects

        self.project_combo = QComboBox()
        for project in projects:
            label = project.name if project.status.value == "active" else f"{project.name} (Archived)"
            self.project_combo.addItem(label, project.id)

        form = QFormLayout()
        form.addRow("Project", self.project_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def selected_project_id(self) -> str | None:
        value = self.project_combo.currentData()
        return str(value) if value else None
