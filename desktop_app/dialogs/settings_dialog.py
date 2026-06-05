from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QComboBox,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from desktop_app.settings.settings_manager import SettingsManager
from desktop_app.state.theme_state import ThemeMode


class SettingsDialog(QDialog):
    def __init__(self, settings_manager: SettingsManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.setWindowTitle("Settings")

        current = settings_manager.current

        self.theme_combo = QComboBox()
        for mode in ThemeMode:
            self.theme_combo.addItem(mode.value.title(), mode.value)
        self.theme_combo.setCurrentIndex(max(0, self.theme_combo.findData(current.theme.value)))

        self.workspace_path_input = QLineEdit(current.workspace_path)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_workspace_path)
        workspace_row = QHBoxLayout()
        workspace_row.addWidget(self.workspace_path_input, 1)
        workspace_row.addWidget(browse_button)

        self.default_provider_input = QLineEdit(current.default_provider)
        self.default_model_input = QLineEdit(current.default_model)
        self.provider_routing_mode_combo = QComboBox()
        for label, value in (
            ("Automatic", "automatic"),
            ("Local First", "local_first"),
            ("Manual", "manual"),
            ("Privacy", "privacy"),
            ("Cost", "cost"),
            ("Latency", "latency"),
        ):
            self.provider_routing_mode_combo.addItem(label, value)
        self.provider_routing_mode_combo.setCurrentIndex(
            max(0, self.provider_routing_mode_combo.findData(current.provider_routing_mode))
        )
        self.local_first_mode_checkbox = QCheckBox("Prefer local providers when available")
        self.local_first_mode_checkbox.setChecked(current.local_first_mode)
        self.embedding_provider_input = QLineEdit(current.embedding_provider)
        self.embedding_selection_combo = QComboBox()
        for label, value in (
            ("Auto", "auto"),
            ("Small", "small"),
            ("Base", "base"),
            ("Large", "large"),
        ):
            self.embedding_selection_combo.addItem(label, value)
        self.embedding_selection_combo.setCurrentIndex(
            max(0, self.embedding_selection_combo.findData(current.embedding_selection))
        )

        self.performance_mode_combo = QComboBox()
        for value in ("automatic", "low_memory", "balanced", "quality", "performance"):
            self.performance_mode_combo.addItem(value.title(), value)
        self.performance_mode_combo.setCurrentIndex(
            max(0, self.performance_mode_combo.findData(current.performance_mode))
        )
        self.low_memory_mode_checkbox = QCheckBox("Enable low memory mode")
        self.low_memory_mode_checkbox.setChecked(current.low_memory_mode)
        self.low_memory_mode_checkbox.toggled.connect(self._apply_low_memory_constraints)
        self.embedding_idle_timeout_input = QLineEdit(str(current.embedding_idle_timeout_seconds))
        self.worker_strategy_combo = QComboBox()
        for label, value in (
            ("Auto", "auto"),
            ("Starter", "starter"),
            ("Standard", "standard"),
            ("Advanced", "advanced"),
            ("Workstation", "workstation"),
            ("Isolated Cold", "isolated_cold"),
        ):
            self.worker_strategy_combo.addItem(label, value)
        self.worker_strategy_combo.setCurrentIndex(
            max(0, self.worker_strategy_combo.findData(current.worker_strategy))
        )

        form = QFormLayout()
        form.addRow("Theme", self.theme_combo)
        form.addRow("Workspace Path", workspace_row)
        form.addRow("Default Provider", self.default_provider_input)
        form.addRow("Default Model", self.default_model_input)
        form.addRow("Provider Routing Mode", self.provider_routing_mode_combo)
        form.addRow("Local First", self.local_first_mode_checkbox)
        form.addRow("Embedding Provider", self.embedding_provider_input)
        form.addRow("Embedding Selection", self.embedding_selection_combo)
        form.addRow("Performance Mode", self.performance_mode_combo)
        form.addRow("Low Memory Mode", self.low_memory_mode_checkbox)
        form.addRow("Embedding Idle Timeout (seconds)", self.embedding_idle_timeout_input)
        form.addRow("Worker Strategy", self.worker_strategy_combo)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.save)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)
        self._apply_low_memory_constraints(self.low_memory_mode_checkbox.isChecked())

    def browse_workspace_path(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self,
            "Workspace Path",
            self.workspace_path_input.text() or str(Path.home()),
        )
        if path:
            self.workspace_path_input.setText(path)

    def save(self) -> None:
        self.settings_manager.update(
            theme=ThemeMode(str(self.theme_combo.currentData())),
            workspace_path=self.workspace_path_input.text().strip(),
            default_provider=self.default_provider_input.text().strip(),
            default_model=self.default_model_input.text().strip(),
            provider_routing_mode=str(self.provider_routing_mode_combo.currentData()),
            local_first_mode=self.local_first_mode_checkbox.isChecked(),
            embedding_provider=self.embedding_provider_input.text().strip(),
            embedding_selection=str(self.embedding_selection_combo.currentData()),
            performance_mode=str(self.performance_mode_combo.currentData()),
            low_memory_mode=self.low_memory_mode_checkbox.isChecked(),
            embedding_idle_timeout_seconds=self._idle_timeout_seconds(),
            worker_strategy=str(self.worker_strategy_combo.currentData()),
        )
        self.accept()

    def _apply_low_memory_constraints(self, enabled: bool) -> None:
        if enabled:
            self.embedding_selection_combo.setCurrentIndex(max(0, self.embedding_selection_combo.findData("small")))
        self.embedding_selection_combo.setEnabled(not enabled)

    def _idle_timeout_seconds(self) -> int:
        try:
            return max(0, int(self.embedding_idle_timeout_input.text().strip()))
        except ValueError:
            return 600
