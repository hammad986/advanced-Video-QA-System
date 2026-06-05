from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from desktop_app.dialogs.provider_test_dialog import ProviderTestConnectionDialog
from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_profile import ProviderName, ProviderProfile


class ProviderManagementDialog(QDialog):
    def __init__(self, provider_manager: ProviderManager, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.provider_manager = provider_manager
        self._profiles: list[ProviderProfile] = []
        self._selected_profile: ProviderProfile | None = None

        self.setWindowTitle("Provider Management")
        self.resize(760, 460)

        self.provider_list = QListWidget()
        self.provider_list.currentRowChanged.connect(self.load_selected_profile)

        self.provider_name_combo = QComboBox()
        for definition in self.provider_manager.registry.all():
            self.provider_name_combo.addItem(definition.display_name, definition.name.value)
        self.provider_name_combo.currentIndexChanged.connect(self.apply_provider_defaults)

        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Leave blank to keep existing key")
        self.base_url_input = QLineEdit()
        self.model_input = QLineEdit()
        self.embedding_model_input = QLineEdit()
        self.enabled_checkbox = QCheckBox("Enabled")
        self.enabled_checkbox.setChecked(True)

        form = QFormLayout()
        form.addRow("Provider", self.provider_name_combo)
        form.addRow("API Key", self.api_key_input)
        form.addRow("Base URL", self.base_url_input)
        form.addRow("Model", self.model_input)
        form.addRow("Embedding Model", self.embedding_model_input)
        form.addRow("", self.enabled_checkbox)

        new_button = QPushButton("New")
        save_button = QPushButton("Save")
        delete_button = QPushButton("Delete")
        enable_button = QPushButton("Enable")
        disable_button = QPushButton("Disable")
        default_button = QPushButton("Set Default")
        test_button = QPushButton("Test")

        new_button.clicked.connect(self.new_profile)
        save_button.clicked.connect(self.save_profile)
        delete_button.clicked.connect(self.delete_profile)
        enable_button.clicked.connect(lambda: self.set_enabled(True))
        disable_button.clicked.connect(lambda: self.set_enabled(False))
        default_button.clicked.connect(self.set_default_provider)
        test_button.clicked.connect(self.test_provider)

        action_row = QHBoxLayout()
        for button in (new_button, save_button, delete_button, enable_button, disable_button, default_button, test_button):
            action_row.addWidget(button)

        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.addLayout(form)
        detail_layout.addLayout(action_row)
        detail_layout.addStretch(1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.provider_list)
        splitter.addWidget(detail)
        splitter.setSizes([240, 520])

        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addWidget(splitter, 1)
        layout.addWidget(close_buttons)

        self.refresh_profiles()
        self.new_profile()

    def refresh_profiles(self) -> None:
        selected_id = self._selected_profile.id if self._selected_profile else ""
        self._profiles = self.provider_manager.list_providers()
        self.provider_list.clear()
        for profile in self._profiles:
            label = f"{profile.provider_name.value} · {profile.model or profile.embedding_model or 'unconfigured'}"
            if not profile.enabled:
                label += " (Disabled)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, profile.id)
            self.provider_list.addItem(item)
        if selected_id:
            for index in range(self.provider_list.count()):
                if self.provider_list.item(index).data(Qt.ItemDataRole.UserRole) == selected_id:
                    self.provider_list.setCurrentRow(index)
                    break

    def load_selected_profile(self, row: int) -> None:
        if row < 0 or row >= len(self._profiles):
            return
        self._selected_profile = self._profiles[row]
        self.provider_name_combo.setCurrentIndex(
            max(0, self.provider_name_combo.findData(self._selected_profile.provider_name.value))
        )
        self.api_key_input.clear()
        self.base_url_input.setText(self._selected_profile.base_url)
        self.model_input.setText(self._selected_profile.model)
        self.embedding_model_input.setText(self._selected_profile.embedding_model)
        self.enabled_checkbox.setChecked(self._selected_profile.enabled)

    def new_profile(self) -> None:
        self._selected_profile = None
        self.provider_name_combo.setCurrentIndex(0)
        self.api_key_input.clear()
        self.enabled_checkbox.setChecked(True)
        self.apply_provider_defaults()
        self.provider_list.clearSelection()

    def apply_provider_defaults(self) -> None:
        if self._selected_profile is not None:
            return
        provider_name = ProviderName(str(self.provider_name_combo.currentData()))
        definition = self.provider_manager.registry.get(provider_name)
        self.base_url_input.setText(definition.default_base_url)
        self.model_input.setText(definition.default_model)
        self.embedding_model_input.setText(definition.default_embedding_model)

    def save_profile(self) -> None:
        provider_name = ProviderName(str(self.provider_name_combo.currentData()))
        if self._selected_profile is None:
            self._selected_profile = self.provider_manager.create_provider(
                provider_name,
                api_key=self.api_key_input.text().strip(),
                base_url=self.base_url_input.text().strip(),
                model=self.model_input.text().strip(),
                embedding_model=self.embedding_model_input.text().strip(),
                enabled=self.enabled_checkbox.isChecked(),
            )
        else:
            profile = self._selected_profile.with_updates(
                provider_name=provider_name,
                api_key=self.api_key_input.text().strip(),
                base_url=self.base_url_input.text().strip(),
                model=self.model_input.text().strip(),
                embedding_model=self.embedding_model_input.text().strip(),
                enabled=self.enabled_checkbox.isChecked(),
            )
            self._selected_profile = self.provider_manager.update_provider(profile)
        self.refresh_profiles()

    def delete_profile(self) -> None:
        if self._selected_profile is None:
            return
        self.provider_manager.delete_provider(self._selected_profile.id)
        self._selected_profile = None
        self.refresh_profiles()
        self.new_profile()

    def set_enabled(self, enabled: bool) -> None:
        if self._selected_profile is None:
            return
        if enabled:
            self._selected_profile = self.provider_manager.enable_provider(self._selected_profile.id)
        else:
            self._selected_profile = self.provider_manager.disable_provider(self._selected_profile.id)
        self.refresh_profiles()

    def set_default_provider(self) -> None:
        if self._selected_profile is None:
            return
        self.provider_manager.switch_provider(self._selected_profile.id)

    def test_provider(self) -> None:
        if self._selected_profile is None:
            self.save_profile()
        if self._selected_profile is None:
            return
        result = self.provider_manager.validate_provider(self._selected_profile.id)
        ProviderTestConnectionDialog(result, self).exec()
