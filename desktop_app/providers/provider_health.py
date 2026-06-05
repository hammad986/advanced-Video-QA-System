from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum
from sqlite3 import Row
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from dotenv import dotenv_values

from desktop_app.database.connection import DatabaseConnection
from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_profile import ProviderName, ProviderProfile
from desktop_app.providers.provider_registry import ProviderRegistry


class ProviderHealthStatus(StrEnum):
    CONFIGURED = "configured"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ProviderHealthResult:
    id: str
    provider: ProviderName
    profile_id: str
    status: ProviderHealthStatus
    configured: bool
    reachable: bool
    authentication_valid: bool
    model_available: bool
    latency_ms: float
    message: str
    checked_at: float
    source: str = ""

    @property
    def responded(self) -> bool:
        return self.reachable and self.authentication_valid

    @classmethod
    def create(
        cls,
        *,
        provider: ProviderName,
        profile_id: str = "",
        status: ProviderHealthStatus,
        configured: bool,
        reachable: bool = False,
        authentication_valid: bool = False,
        model_available: bool = False,
        latency_ms: float = 0.0,
        message: str = "",
        source: str = "",
    ) -> "ProviderHealthResult":
        return cls(
            id=str(uuid.uuid4()),
            provider=provider,
            profile_id=profile_id,
            status=status,
            configured=configured,
            reachable=reachable,
            authentication_valid=authentication_valid,
            model_available=model_available,
            latency_ms=max(0.0, latency_ms),
            message=message[:500],
            checked_at=time.time(),
            source=source,
        )


class ProviderHealthRepository:
    def __init__(self, connection: DatabaseConnection) -> None:
        self.connection = connection

    def save(self, result: ProviderHealthResult) -> ProviderHealthResult:
        with self.connection.connect() as connection:
            connection.execute(
                """
                INSERT INTO provider_health_checks (
                    id, provider, profile_id, status, configured, reachable,
                    authentication_valid, model_available, latency_ms, message, checked_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result.id,
                    result.provider.value,
                    result.profile_id,
                    result.status.value,
                    int(result.configured),
                    int(result.reachable),
                    int(result.authentication_valid),
                    int(result.model_available),
                    result.latency_ms,
                    result.message,
                    result.checked_at,
                ),
            )
        return result

    def list_recent(self, *, limit: int = 100) -> list[ProviderHealthResult]:
        with self.connection.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM provider_health_checks
                ORDER BY checked_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._row_to_result(row) for row in rows]

    def _row_to_result(self, row: Row) -> ProviderHealthResult:
        return ProviderHealthResult(
            id=str(row["id"]),
            provider=ProviderName(str(row["provider"])),
            profile_id=str(row["profile_id"] or ""),
            status=ProviderHealthStatus(str(row["status"])),
            configured=bool(row["configured"]),
            reachable=bool(row["reachable"]),
            authentication_valid=bool(row["authentication_valid"]),
            model_available=bool(row["model_available"]),
            latency_ms=float(row["latency_ms"]),
            message=str(row["message"] or ""),
            checked_at=float(row["checked_at"]),
        )


class ProviderHealthService:
    ENV_KEYS: dict[ProviderName, tuple[str, ...]] = {
        ProviderName.GEMINI: ("GEMINI_API_KEY",),
        ProviderName.OPENAI: ("OPENAI_API_KEY",),
        ProviderName.CLAUDE: ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
        ProviderName.OPENROUTER: ("OPENROUTER_API_KEY",),
        ProviderName.GROQ: ("GROQ_API_KEY",),
        ProviderName.MISTRAL: ("MISTRAL_API_KEY",),
        ProviderName.OLLAMA: ("OLLAMA_BASE_URL",),
        ProviderName.LM_STUDIO: ("LM_STUDIO_BASE_URL",),
        ProviderName.OPENAI_COMPATIBLE: ("OPENAI_COMPATIBLE_BASE_URL", "LOCAL_OPENAI_BASE_URL"),
    }

    def __init__(
        self,
        *,
        repository: ProviderHealthRepository | None = None,
        provider_manager: ProviderManager | None = None,
        registry: ProviderRegistry | None = None,
        env_path: str = ".env",
        timeout_seconds: float = 8.0,
    ) -> None:
        self.repository = repository
        self.provider_manager = provider_manager
        self.registry = registry or ProviderRegistry()
        self.env_path = env_path
        self.timeout_seconds = timeout_seconds

    def check_all(self, *, include_env: bool = True) -> list[ProviderHealthResult]:
        profiles = self._configured_profiles(include_env=include_env)
        seen = {profile.provider_name for profile in profiles}
        results = [self.check_profile(profile, source="profile" if profile.id else "env") for profile in profiles]
        for definition in self.registry.all():
            if definition.name in seen:
                continue
            results.append(
                ProviderHealthResult.create(
                    provider=definition.name,
                    status=ProviderHealthStatus.UNAVAILABLE,
                    configured=False,
                    message="Provider is not configured.",
                    source="none",
                )
            )
        return results

    def check_profile(self, profile: ProviderProfile, *, source: str = "profile") -> ProviderHealthResult:
        definition = self.registry.get(profile.provider_name)
        if definition.requires_api_key and not profile.api_key:
            return self._save(
                ProviderHealthResult.create(
                    provider=profile.provider_name,
                    profile_id=profile.id,
                    status=ProviderHealthStatus.FAILED,
                    configured=True,
                    message="API key is missing.",
                    source=source,
                )
            )
        model = profile.model or definition.default_model
        base_url = (profile.base_url or definition.default_base_url).rstrip("/")
        started = time.perf_counter()
        try:
            status_code, payload = self._request_models(profile.provider_name, base_url, profile.api_key)
            latency_ms = (time.perf_counter() - started) * 1000.0
            authentication_valid = 200 <= status_code < 300
            model_available = self._model_available(profile.provider_name, payload, model)
            status = ProviderHealthStatus.HEALTHY if authentication_valid and model_available else ProviderHealthStatus.DEGRADED
            message = "Provider responded and model is available." if model_available else "Provider responded but model was not found."
            return self._save(
                ProviderHealthResult.create(
                    provider=profile.provider_name,
                    profile_id=profile.id,
                    status=status,
                    configured=True,
                    reachable=True,
                    authentication_valid=authentication_valid,
                    model_available=model_available,
                    latency_ms=latency_ms,
                    message=message,
                    source=source,
                )
            )
        except HTTPError as error:
            latency_ms = (time.perf_counter() - started) * 1000.0
            authentication_valid = error.code not in {401, 403}
            return self._save(
                ProviderHealthResult.create(
                    provider=profile.provider_name,
                    profile_id=profile.id,
                    status=ProviderHealthStatus.FAILED,
                    configured=True,
                    reachable=True,
                    authentication_valid=authentication_valid,
                    latency_ms=latency_ms,
                    message=f"HTTP {error.code}: provider endpoint rejected the request.",
                    source=source,
                )
            )
        except (TimeoutError, URLError, OSError) as error:
            latency_ms = (time.perf_counter() - started) * 1000.0
            return self._save(
                ProviderHealthResult.create(
                    provider=profile.provider_name,
                    profile_id=profile.id,
                    status=ProviderHealthStatus.FAILED,
                    configured=True,
                    latency_ms=latency_ms,
                    message=f"Provider endpoint was not reachable: {type(error).__name__}.",
                    source=source,
                )
            )

    def _configured_profiles(self, *, include_env: bool) -> list[ProviderProfile]:
        profiles = self.provider_manager.list_providers(enabled_only=True) if self.provider_manager else []
        if include_env:
            profiles.extend(self._profiles_from_env(existing={profile.provider_name for profile in profiles}))
        return profiles

    def _profiles_from_env(self, *, existing: set[ProviderName]) -> list[ProviderProfile]:
        if not os.path.exists(self.env_path):
            return []
        env = dict(dotenv_values(self.env_path))
        profiles: list[ProviderProfile] = []
        for provider_name, keys in self.ENV_KEYS.items():
            if provider_name in existing:
                continue
            value = next((env.get(key, "").strip() for key in keys if env.get(key, "").strip()), "")
            if not value:
                continue
            definition = self.registry.get(provider_name)
            api_key = "" if definition.is_local else value
            base_url = value if definition.is_local else definition.default_base_url
            profiles.append(
                ProviderProfile.create(
                    provider_name,
                    api_key=api_key,
                    base_url=base_url,
                    model=definition.default_model,
                    embedding_model=definition.default_embedding_model,
                ).with_updates(id="")
            )
        return profiles

    def _request_models(self, provider_name: ProviderName, base_url: str, api_key: str) -> tuple[int, object]:
        if provider_name == ProviderName.GEMINI:
            url = f"{base_url}/v1beta/models?key={api_key}"
            headers: dict[str, str] = {}
        elif provider_name == ProviderName.OLLAMA:
            url = f"{base_url}/api/tags"
            headers = {}
        elif provider_name == ProviderName.CLAUDE:
            url = f"{base_url}/v1/models"
            headers = {"x-api-key": api_key, "anthropic-version": "2023-06-01"}
        else:
            url = urljoin(f"{base_url}/", "models")
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        request = Request(url, headers=headers)
        with urlopen(request, timeout=self.timeout_seconds) as response:
            body = response.read(1_000_000).decode("utf-8", errors="replace")
            try:
                payload: object = json.loads(body) if body else {}
            except json.JSONDecodeError:
                payload = {}
            return int(response.status), payload

    def _model_available(self, provider_name: ProviderName, payload: object, model: str) -> bool:
        if not model:
            return True
        model_ids = self._extract_model_ids(provider_name, payload)
        if not model_ids:
            return True
        return model in model_ids or any(model == item.split("/")[-1] for item in model_ids)

    def _extract_model_ids(self, provider_name: ProviderName, payload: object) -> set[str]:
        if not isinstance(payload, dict):
            return set()
        key = "models" if provider_name in {ProviderName.GEMINI, ProviderName.OLLAMA} else "data"
        items = payload.get(key)
        if not isinstance(items, list):
            return set()
        ids: set[str] = set()
        for item in items:
            if not isinstance(item, dict):
                continue
            value = item.get("name") or item.get("id") or item.get("model")
            if isinstance(value, str):
                ids.add(value)
                ids.add(value.removeprefix("models/"))
        return ids

    def _save(self, result: ProviderHealthResult) -> ProviderHealthResult:
        if self.repository is not None and result.configured:
            self.repository.save(result)
        return result
