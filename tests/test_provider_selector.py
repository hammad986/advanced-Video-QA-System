from __future__ import annotations

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_profile import ProviderName
from desktop_app.settings.settings_manager import SettingsManager
from desktop_app.settings.settings_repository import SettingsRepository
from desktop_app.widgets.provider_selector import ProviderSelector


def test_provider_selector_lists_enabled_providers(qapp, tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    settings = SettingsManager(
        SettingsRepository(database.connection),
        default_workspace_path=tmp_path / "projects",
    )
    manager = ProviderManager(database.connection, settings)
    enabled = manager.create_provider(ProviderName.OLLAMA, model="llama3.2")
    disabled = manager.create_provider(ProviderName.LM_STUDIO, model="local-model", enabled=False)

    selector = ProviderSelector(manager)

    assert selector.provider_combo.findData(enabled.id) >= 0
    assert selector.provider_combo.findData(disabled.id) == -1
