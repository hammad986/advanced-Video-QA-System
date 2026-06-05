from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_profile import ProviderProfile


class ProviderSelector(QWidget):
    provider_selected = Signal(str)

    def __init__(self, provider_manager: ProviderManager | None = None, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.provider_manager = provider_manager
        self._profiles: list[ProviderProfile] = []

        self.label = QLabel("Provider")
        self.provider_combo = QComboBox()
        self.provider_combo.currentIndexChanged.connect(self._emit_selected_provider)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 4)
        layout.addWidget(self.label)
        layout.addWidget(self.provider_combo, 1)

        self.refresh()

    def refresh(self) -> None:
        self.provider_combo.blockSignals(True)
        self.provider_combo.clear()
        self.provider_combo.addItem("No Provider", "")
        if self.provider_manager is None:
            self.provider_combo.setEnabled(False)
            self.provider_combo.blockSignals(False)
            return

        self.provider_combo.setEnabled(True)
        self._profiles = self.provider_manager.list_providers(enabled_only=True)
        default_provider = self.provider_manager.settings_manager.current.default_provider
        for profile in self._profiles:
            label = f"{profile.provider_name.value} · {profile.model or profile.embedding_model}"
            self.provider_combo.addItem(label, profile.id)
        if default_provider:
            index = self.provider_combo.findData(default_provider)
            if index >= 0:
                self.provider_combo.setCurrentIndex(index)
        self.provider_combo.blockSignals(False)

    def current_provider_id(self) -> str | None:
        value = self.provider_combo.currentData()
        return str(value) if value else None

    def _emit_selected_provider(self) -> None:
        provider_id = self.current_provider_id()
        if not provider_id or self.provider_manager is None:
            return
        self.provider_manager.switch_provider(provider_id)
        self.provider_selected.emit(provider_id)

