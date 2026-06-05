from __future__ import annotations

import sys

import pytest

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_profile import ProviderName
from desktop_app.providers.provider_validator import ValidationStatus
from desktop_app.settings.settings_manager import SettingsManager
from desktop_app.settings.settings_repository import SettingsRepository


@pytest.fixture()
def provider_manager(tmp_path) -> ProviderManager:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    settings = SettingsManager(
        SettingsRepository(database.connection),
        default_workspace_path=tmp_path / "projects",
    )
    return ProviderManager(database.connection, settings)


def test_provider_manager_create_update_delete_provider(provider_manager: ProviderManager) -> None:
    profile = provider_manager.create_provider(
        ProviderName.OPENAI,
        api_key="sk-test-secret",
        model="gpt-test",
        embedding_model="text-embedding-test",
    )

    assert provider_manager.settings_manager.current.default_provider == profile.id
    assert provider_manager.get_provider(profile.id).api_key == "sk-test-secret"  # type: ignore[union-attr]

    updated = provider_manager.update_provider(profile.with_updates(model="gpt-updated"))
    assert updated.model == "gpt-updated"
    assert provider_manager.get_provider(profile.id).model == "gpt-updated"  # type: ignore[union-attr]

    assert provider_manager.delete_provider(profile.id) is True
    assert provider_manager.get_provider(profile.id) is None


def test_provider_manager_enable_disable_switch_provider(provider_manager: ProviderManager) -> None:
    openai = provider_manager.create_provider(ProviderName.OPENAI, api_key="sk-test", model="gpt-test")
    ollama = provider_manager.create_provider(ProviderName.OLLAMA, model="llama3.2")

    provider_manager.switch_provider(ollama.id)
    assert provider_manager.settings_manager.current.default_provider == ollama.id

    disabled = provider_manager.disable_provider(ollama.id)
    assert disabled is not None
    assert disabled.enabled is False
    assert provider_manager.settings_manager.current.default_provider == ""

    enabled = provider_manager.enable_provider(ollama.id)
    assert enabled is not None
    provider_manager.switch_provider(openai.id)
    assert provider_manager.settings_manager.current.default_provider == openai.id


def test_provider_validator_reports_missing_api_key(provider_manager: ProviderManager) -> None:
    profile = provider_manager.create_provider(ProviderName.CLAUDE, model="claude-test")

    result = provider_manager.validate_provider(profile.id)

    assert result.status == ValidationStatus.FAILED
    assert "API key" in result.message


def test_provider_api_key_is_not_stored_plaintext(tmp_path) -> None:
    if sys.platform != "win32":
        pytest.skip("Provider key encryption uses Windows DPAPI.")
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    settings = SettingsManager(
        SettingsRepository(database.connection),
        default_workspace_path=tmp_path / "projects",
    )
    manager = ProviderManager(database.connection, settings)

    profile = manager.create_provider(
        ProviderName.GEMINI,
        api_key="gemini-super-secret",
        model="gemini-test",
    )

    with database.connection.connect() as connection:
        row = connection.execute(
            "SELECT api_key_encrypted FROM provider_profiles WHERE id = ?",
            (profile.id,),
        ).fetchone()

    stored_value = str(row["api_key_encrypted"])
    assert stored_value.startswith(("wincred:", "dpapi:"))
    assert "gemini-super-secret" not in stored_value
    assert manager.get_provider(profile.id).api_key == "gemini-super-secret"  # type: ignore[union-attr]
