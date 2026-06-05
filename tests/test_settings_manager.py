from __future__ import annotations

from desktop_app.database.database_manager import DatabaseManager
from desktop_app.settings.settings_manager import SettingsManager
from desktop_app.settings.settings_repository import SettingsRepository
from desktop_app.state.theme_state import ThemeMode


def test_settings_manager_persists_required_settings(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    repository = SettingsRepository(database.connection)
    manager = SettingsManager(repository, default_workspace_path=tmp_path / "projects")

    manager.update(
        theme=ThemeMode.LIGHT,
        workspace_path=str(tmp_path / "workspace"),
        default_provider="provider-1",
        default_model="model-1",
        embedding_provider="provider-2",
        embedding_selection="base",
        performance_mode="performance",
        low_memory_mode=False,
        embedding_idle_timeout_seconds=123,
        worker_strategy="advanced",
        provider_routing_mode="local_first",
        local_first_mode=True,
        first_run_completed=True,
    )

    reloaded = SettingsManager(repository, default_workspace_path=tmp_path / "projects")

    assert reloaded.current.theme == ThemeMode.LIGHT
    assert reloaded.current.workspace_path == str(tmp_path / "workspace")
    assert reloaded.current.default_provider == "provider-1"
    assert reloaded.current.default_model == "model-1"
    assert reloaded.current.embedding_provider == "provider-2"
    assert reloaded.current.embedding_selection == "base"
    assert reloaded.current.performance_mode == "performance"
    assert reloaded.current.low_memory_mode is False
    assert reloaded.current.embedding_idle_timeout_seconds == 123
    assert reloaded.current.worker_strategy == "advanced"
    assert reloaded.current.provider_routing_mode == "local_first"
    assert reloaded.current.local_first_mode is True
    assert reloaded.current.first_run_completed is True


def test_low_memory_mode_forces_small_embedding_selection(tmp_path) -> None:
    database = DatabaseManager(tmp_path / "app.db")
    database.initialize()
    repository = SettingsRepository(database.connection)
    manager = SettingsManager(repository, default_workspace_path=tmp_path / "projects")

    manager.update(embedding_selection="large", low_memory_mode=True)
    reloaded = SettingsManager(repository, default_workspace_path=tmp_path / "projects")

    assert reloaded.current.low_memory_mode is True
    assert reloaded.current.embedding_selection == "small"
