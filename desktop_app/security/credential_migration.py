from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from dotenv import dotenv_values

from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_profile import ProviderName, ProviderProfile


@dataclass(frozen=True)
class CredentialSecurityReport:
    env_path: Path
    plaintext_keys_found: tuple[str, ...]
    migrated_provider_count: int
    sanitized_env: bool

    @property
    def secure_storage_active(self) -> bool:
        return True


class EnvCredentialMigrationService:
    ENV_KEYS: dict[ProviderName, tuple[str, ...]] = {
        ProviderName.GEMINI: ("GEMINI_API_KEY",),
        ProviderName.OPENAI: ("OPENAI_API_KEY",),
        ProviderName.CLAUDE: ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
        ProviderName.OPENROUTER: ("OPENROUTER_API_KEY",),
        ProviderName.GROQ: ("GROQ_API_KEY",),
        ProviderName.MISTRAL: ("MISTRAL_API_KEY",),
    }

    def __init__(self, provider_manager: ProviderManager, env_path: Path) -> None:
        self.provider_manager = provider_manager
        self.env_path = env_path

    def audit(self) -> CredentialSecurityReport:
        keys = self._plaintext_keys()
        migrated = self.provider_manager.migrate_credentials_to_windows_manager()
        return CredentialSecurityReport(self.env_path, tuple(keys), migrated, False)

    def migrate_env_credentials(self, *, sanitize_env: bool = False) -> CredentialSecurityReport:
        keys = self._plaintext_keys()
        env = dict(dotenv_values(self.env_path)) if self.env_path.exists() else {}
        existing = {profile.provider_name for profile in self.provider_manager.list_providers()}
        migrated = self.provider_manager.migrate_credentials_to_windows_manager()
        for provider_name, candidate_keys in self.ENV_KEYS.items():
            value = next((str(env.get(key, "")).strip() for key in candidate_keys if str(env.get(key, "")).strip()), "")
            if not value or provider_name in existing:
                continue
            definition = self.provider_manager.registry.get(provider_name)
            self.provider_manager.create_provider(
                provider_name,
                api_key=value,
                base_url=definition.default_base_url,
                model=definition.default_model,
                embedding_model=definition.default_embedding_model,
                enabled=True,
            )
            migrated += 1
        sanitized = False
        if sanitize_env and keys:
            self._sanitize_env(keys)
            sanitized = True
        return CredentialSecurityReport(self.env_path, tuple(keys), migrated, sanitized)

    def _plaintext_keys(self) -> list[str]:
        if not self.env_path.exists():
            return []
        env = dict(dotenv_values(self.env_path))
        keys: list[str] = []
        for candidate_keys in self.ENV_KEYS.values():
            for key in candidate_keys:
                if str(env.get(key, "")).strip():
                    keys.append(key)
        return keys

    def _sanitize_env(self, keys: list[str]) -> None:
        lines = self.env_path.read_text(encoding="utf-8").splitlines()
        key_set = set(keys)
        sanitized: list[str] = []
        for line in lines:
            stripped = line.strip()
            if "=" not in stripped or stripped.startswith("#"):
                sanitized.append(line)
                continue
            key = stripped.split("=", 1)[0].strip()
            if key in key_set:
                sanitized.append(f"{key}=")
                sanitized.append(f"# {key} migrated to Windows Credential Manager by Advanced Video QA Pro.")
            else:
                sanitized.append(line)
        self.env_path.write_text("\n".join(sanitized) + "\n", encoding="utf-8")
