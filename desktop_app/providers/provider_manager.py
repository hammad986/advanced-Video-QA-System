from __future__ import annotations

import time
from sqlite3 import Row

from desktop_app.database.connection import DatabaseConnection
from desktop_app.providers.provider_profile import ProviderName, ProviderProfile
from desktop_app.providers.provider_registry import ProviderRegistry
from desktop_app.providers.provider_validator import ProviderValidator, ValidationResult
from desktop_app.security.credential_store import LocalCredentialStore
from desktop_app.settings.settings_manager import SettingsManager


class ProviderManager:
    def __init__(
        self,
        connection: DatabaseConnection,
        settings_manager: SettingsManager,
        *,
        registry: ProviderRegistry | None = None,
        validator: ProviderValidator | None = None,
        credential_store: LocalCredentialStore | None = None,
    ) -> None:
        self.connection = connection
        self.settings_manager = settings_manager
        self.registry = registry or ProviderRegistry()
        self.validator = validator or ProviderValidator(self.registry)
        self.credential_store = credential_store or LocalCredentialStore()

    def create_provider(
        self,
        provider_name: ProviderName,
        *,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        embedding_model: str = "",
        enabled: bool = True,
    ) -> ProviderProfile:
        definition = self.registry.get(provider_name)
        profile = ProviderProfile.create(
            provider_name,
            api_key=api_key,
            base_url=base_url or definition.default_base_url,
            model=model or definition.default_model,
            embedding_model=embedding_model or definition.default_embedding_model,
            enabled=enabled,
        )
        self._save(profile)
        if enabled and not self.settings_manager.current.default_provider:
            self.switch_provider(profile.id)
        return profile

    def update_provider(self, profile: ProviderProfile) -> ProviderProfile:
        updated = profile.with_updates()
        self._save(updated)
        current = self.settings_manager.current
        if current.default_provider == updated.id:
            self.settings_manager.update(
                default_model=updated.model,
                embedding_provider=updated.id if updated.embedding_model else current.embedding_provider,
            )
        return updated

    def delete_provider(self, provider_id: str) -> bool:
        stored_reference = self._stored_secret_reference(provider_id)
        with self.connection.connect() as connection:
            cursor = connection.execute("DELETE FROM provider_profiles WHERE id = ?", (provider_id,))
        if stored_reference:
            self.credential_store.delete_secret(stored_reference)
        current = self.settings_manager.current
        if current.default_provider == provider_id:
            self.settings_manager.update(default_provider="", default_model="")
        if current.embedding_provider == provider_id:
            self.settings_manager.update(embedding_provider="")
        return cursor.rowcount > 0

    def enable_provider(self, provider_id: str) -> ProviderProfile | None:
        profile = self.get_provider(provider_id)
        if not profile:
            return None
        return self.update_provider(profile.with_updates(enabled=True))

    def disable_provider(self, provider_id: str) -> ProviderProfile | None:
        profile = self.get_provider(provider_id)
        if not profile:
            return None
        updated = self.update_provider(profile.with_updates(enabled=False))
        current = self.settings_manager.current
        if current.default_provider == provider_id:
            self.settings_manager.update(default_provider="", default_model="")
        if current.embedding_provider == provider_id:
            self.settings_manager.update(embedding_provider="")
        return updated

    def switch_provider(self, provider_id: str) -> ProviderProfile:
        profile = self.get_provider(provider_id)
        if profile is None:
            raise ValueError("Provider profile does not exist.")
        if not profile.enabled:
            raise ValueError("Disabled provider cannot be selected.")
        self.settings_manager.update(default_provider=profile.id, default_model=profile.model)
        return profile

    def validate_provider(self, provider_id: str) -> ValidationResult:
        profile = self.get_provider(provider_id)
        if profile is None:
            raise ValueError("Provider profile does not exist.")
        return self.validator.validate(profile)

    def migrate_credentials_to_windows_manager(self) -> int:
        migrated = 0
        for profile in self.list_providers():
            if not profile.api_key:
                continue
            stored_reference = self._stored_secret_reference(profile.id)
            if stored_reference.startswith("wincred:"):
                continue
            self._save(profile)
            migrated += 1
        return migrated

    def list_providers(self, *, enabled_only: bool = False) -> list[ProviderProfile]:
        sql = "SELECT * FROM provider_profiles"
        params: tuple[object, ...] = ()
        if enabled_only:
            sql += " WHERE enabled = ?"
            params = (1,)
        sql += " ORDER BY provider_name, updated_at DESC"
        with self.connection.connect() as connection:
            rows = connection.execute(sql, params).fetchall()
        return [self._row_to_profile(row) for row in rows]

    def get_provider(self, provider_id: str) -> ProviderProfile | None:
        with self.connection.connect() as connection:
            row = connection.execute("SELECT * FROM provider_profiles WHERE id = ?", (provider_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_profile(row)

    def _save(self, profile: ProviderProfile) -> None:
        encrypted_api_key = self.credential_store.store_secret(profile.id, profile.api_key)
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO provider_profiles (
                    id, provider_name, api_key_encrypted, base_url, model,
                    embedding_model, enabled, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    provider_name = excluded.provider_name,
                    api_key_encrypted = CASE
                        WHEN excluded.api_key_encrypted = '' THEN provider_profiles.api_key_encrypted
                        ELSE excluded.api_key_encrypted
                    END,
                    base_url = excluded.base_url,
                    model = excluded.model,
                    embedding_model = excluded.embedding_model,
                    enabled = excluded.enabled,
                    updated_at = excluded.updated_at
                """,
                (
                    profile.id,
                    profile.provider_name.value,
                    encrypted_api_key,
                    profile.base_url,
                    profile.model,
                    profile.embedding_model,
                    int(profile.enabled),
                    profile.created_at or time.time(),
                    profile.updated_at or time.time(),
                ),
            )

    def _row_to_profile(self, row: Row) -> ProviderProfile:
        encrypted_api_key = str(row["api_key_encrypted"] or "")
        return ProviderProfile(
            id=str(row["id"]),
            provider_name=ProviderName(str(row["provider_name"])),
            api_key=self.credential_store.retrieve_secret(encrypted_api_key) if encrypted_api_key else "",
            base_url=str(row["base_url"] or ""),
            model=str(row["model"] or ""),
            embedding_model=str(row["embedding_model"] or ""),
            enabled=bool(row["enabled"]),
            created_at=float(row["created_at"]),
            updated_at=float(row["updated_at"]),
        )

    def _stored_secret_reference(self, provider_id: str) -> str:
        with self.connection.connect() as connection:
            row = connection.execute(
                "SELECT api_key_encrypted FROM provider_profiles WHERE id = ?",
                (provider_id,),
            ).fetchone()
        return str(row["api_key_encrypted"] or "") if row else ""
