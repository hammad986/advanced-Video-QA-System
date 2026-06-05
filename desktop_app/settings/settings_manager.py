from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path

from desktop_app.settings.settings_repository import SettingsRepository
from desktop_app.state.theme_state import ThemeMode


@dataclass(frozen=True)
class AppSettings:
    theme: ThemeMode
    workspace_path: str
    default_provider: str
    default_model: str
    embedding_provider: str
    embedding_selection: str
    performance_mode: str
    low_memory_mode: bool
    embedding_idle_timeout_seconds: int
    worker_strategy: str
    provider_routing_mode: str
    local_first_mode: bool
    first_run_completed: bool


class SettingsManager:
    KEY_THEME = "theme"
    KEY_WORKSPACE_PATH = "workspace_path"
    KEY_DEFAULT_PROVIDER = "default_provider"
    KEY_DEFAULT_MODEL = "default_model"
    KEY_EMBEDDING_PROVIDER = "embedding_provider"
    KEY_EMBEDDING_SELECTION = "embedding_selection"
    KEY_PERFORMANCE_MODE = "performance_mode"
    KEY_LOW_MEMORY_MODE = "low_memory_mode"
    KEY_EMBEDDING_IDLE_TIMEOUT_SECONDS = "embedding_idle_timeout_seconds"
    KEY_WORKER_STRATEGY = "worker_strategy"
    KEY_PROVIDER_ROUTING_MODE = "provider_routing_mode"
    KEY_LOCAL_FIRST_MODE = "local_first_mode"
    KEY_FIRST_RUN_COMPLETED = "first_run_completed"

    def __init__(self, repository: SettingsRepository, *, default_workspace_path: Path) -> None:
        self.repository = repository
        self.default_workspace_path = default_workspace_path
        self.current = self.load()

    def load(self) -> AppSettings:
        theme_value = self.repository.get(self.KEY_THEME, ThemeMode.DARK.value)
        try:
            theme = ThemeMode(theme_value)
        except ValueError:
            theme = ThemeMode.DARK
        low_memory_value = self.repository.get(self.KEY_LOW_MEMORY_MODE, "false").strip().lower()
        local_first_value = self.repository.get(self.KEY_LOCAL_FIRST_MODE, "false").strip().lower()
        first_run_value = self.repository.get(self.KEY_FIRST_RUN_COMPLETED, "false").strip().lower()
        idle_timeout_value = self.repository.get(self.KEY_EMBEDDING_IDLE_TIMEOUT_SECONDS, "600")
        try:
            idle_timeout = int(idle_timeout_value)
        except ValueError:
            idle_timeout = 600
        low_memory_mode = low_memory_value in {"1", "true", "yes", "on"}
        embedding_selection = self.repository.get(self.KEY_EMBEDDING_SELECTION, "auto")
        if low_memory_mode:
            embedding_selection = "small"
        return AppSettings(
            theme=theme,
            workspace_path=self.repository.get(self.KEY_WORKSPACE_PATH, str(self.default_workspace_path)),
            default_provider=self.repository.get(self.KEY_DEFAULT_PROVIDER, ""),
            default_model=self.repository.get(self.KEY_DEFAULT_MODEL, ""),
            embedding_provider=self.repository.get(self.KEY_EMBEDDING_PROVIDER, ""),
            embedding_selection=embedding_selection,
            performance_mode=self.repository.get(self.KEY_PERFORMANCE_MODE, "balanced"),
            low_memory_mode=low_memory_mode,
            embedding_idle_timeout_seconds=max(0, idle_timeout),
            worker_strategy=self.repository.get(self.KEY_WORKER_STRATEGY, "auto"),
            provider_routing_mode=self.repository.get(self.KEY_PROVIDER_ROUTING_MODE, "automatic"),
            local_first_mode=local_first_value in {"1", "true", "yes", "on"},
            first_run_completed=first_run_value in {"1", "true", "yes", "on"},
        )

    def save(self, settings: AppSettings) -> AppSettings:
        self.repository.set_many(
            {
                self.KEY_THEME: settings.theme.value,
                self.KEY_WORKSPACE_PATH: settings.workspace_path,
                self.KEY_DEFAULT_PROVIDER: settings.default_provider,
                self.KEY_DEFAULT_MODEL: settings.default_model,
                self.KEY_EMBEDDING_PROVIDER: settings.embedding_provider,
                self.KEY_EMBEDDING_SELECTION: "small" if settings.low_memory_mode else settings.embedding_selection,
                self.KEY_PERFORMANCE_MODE: settings.performance_mode,
                self.KEY_LOW_MEMORY_MODE: "true" if settings.low_memory_mode else "false",
                self.KEY_EMBEDDING_IDLE_TIMEOUT_SECONDS: str(settings.embedding_idle_timeout_seconds),
                self.KEY_WORKER_STRATEGY: settings.worker_strategy,
                self.KEY_PROVIDER_ROUTING_MODE: settings.provider_routing_mode,
                self.KEY_LOCAL_FIRST_MODE: "true" if settings.local_first_mode else "false",
                self.KEY_FIRST_RUN_COMPLETED: "true" if settings.first_run_completed else "false",
            }
        )
        self.current = settings
        return self.current

    def update(self, **changes: object) -> AppSettings:
        next_settings = replace(self.current, **changes)
        return self.save(next_settings)
