from __future__ import annotations

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QVBoxLayout, QWidget

from desktop_app.providers.provider_validator import ValidationResult


class ProviderTestConnectionDialog(QDialog):
    def __init__(self, result: ValidationResult, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Provider Test Connection")

        message = QLabel(f"Status: {result.status.value.title()}\n\n{result.message}")
        message.setWordWrap(True)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        buttons.accepted.connect(self.accept)

        layout = QVBoxLayout(self)
        layout.addWidget(message)
        layout.addWidget(buttons)

