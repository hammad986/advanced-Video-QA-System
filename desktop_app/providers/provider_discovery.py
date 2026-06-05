from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

from dotenv import dotenv_values

from desktop_app.providers.provider_capabilities import ProviderCapability, ProviderCapabilityRegistry
from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_profile import ProviderName, ProviderProfile
from desktop_app.providers.provider_registry import ProviderRegistry
from desktop_app.providers.provider_validator import ProviderValidator, ValidationStatus


class ProviderHealthStatus(StrEnum):
    CONFIGURED = "configured"
    REACHABLE = "reachable"
    HEALTHY = "healthy"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True)
class ProviderDiscoveryResult:
    provider_name: ProviderName
    status: ProviderHealthStatus
    configured: bool
    reachable: bool
    healthy: bool
    source: str
    profile_id: str = ""
    model: str = ""
    base_url: str = ""
    capability: ProviderCapability | None = None
    message: str = ""

    @property
    def usable(self) -> bool:
        return self.configured and self.status in {
            ProviderHealthStatus.CONFIGURED,
            ProviderHealthStatus.REACHABLE,
            ProviderHealthStatus.HEALTHY,
        }


class ProviderDiscoveryService:
    ENV_KEYS: dict[ProviderName, tuple[str, ...]] = {
        ProviderName.GEMINI: ("GEMINI_API_KEY",),
        ProviderName.OPENAI: ("OPENAI_API_KEY",),
        ProviderName.CLAUDE: ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY"),
        ProviderName.OPENROUTER: ("OPENROUTER_API_KEY",),
        ProviderName.GROQ: ("GROQ_API_KEY",),
        ProviderName.MISTRAL: ("MISTRAL_API_KEY",),
        ProviderName.HUGGINGFACE: ("HF_TOKEN", "HUGGINGFACE_API_KEY"),
        ProviderName.OLLAMA: ("OLLAMA_BASE_URL",),
        ProviderName.LM_STUDIO: ("LM_STUDIO_BASE_URL",),
        ProviderName.OPENAI_COMPATIBLE: ("OPENAI_COMPATIBLE_BASE_URL", "LOCAL_OPENAI_BASE_URL"),
    }

    def __init__(
        self,
        *,
        provider_manager: ProviderManager | None = None,
        registry: ProviderRegistry | None = None,
        validator: ProviderValidator | None = None,
        capability_registry: ProviderCapabilityRegistry | None = None,
        env_path: str = ".env",
        reachability_timeout_seconds: float = 0.25,
    ) -> None:
        self.provider_manager = provider_manager
        self.registry = registry or ProviderRegistry()
        self.validator = validator or ProviderValidator(self.registry)
        self.capability_registry = capability_registry or ProviderCapabilityRegistry()
        self.env_path = env_path
        self.reachability_timeout_seconds = reachability_timeout_seconds

    def discover(self, *, check_reachability: bool = True) -> list[ProviderDiscoveryResult]:
        env = dict(dotenv_values(self.env_path)) if os.path.exists(self.env_path) else {}
        profiles = self.provider_manager.list_providers(enabled_only=False) if self.provider_manager else []
        profile_by_provider: dict[ProviderName, ProviderProfile] = {}
        for profile in profiles:
            if profile.enabled and profile.provider_name not in profile_by_provider:
                profile_by_provider[profile.provider_name] = profile
        results: list[ProviderDiscoveryResult] = []
        for definition in self.registry.all():
            profile = profile_by_provider.get(definition.name)
            if profile is not None:
                results.append(self._from_profile(profile, check_reachability=check_reachability))
            else:
                results.append(self._from_environment(definition.name, env, check_reachability=check_reachability))
        return results

    def usable(self, *, check_reachability: bool = False) -> list[ProviderDiscoveryResult]:
        return [result for result in self.discover(check_reachability=check_reachability) if result.usable]

    def _from_profile(self, profile: ProviderProfile, *, check_reachability: bool) -> ProviderDiscoveryResult:
        validation = self.validator.validate(profile)
        reachable = self._reachable(profile.base_url) if check_reachability and profile.base_url else False
        healthy = validation.status == ValidationStatus.HEALTHY and (reachable or not self.registry.get(profile.provider_name).is_local)
        status = self._status(configured=validation.is_usable, reachable=reachable, healthy=healthy)
        return ProviderDiscoveryResult(
            provider_name=profile.provider_name,
            status=status,
            configured=validation.is_usable,
            reachable=reachable,
            healthy=healthy,
            source="profile",
            profile_id=profile.id,
            model=profile.model,
            base_url=profile.base_url,
            capability=self.capability_registry.get(profile.provider_name),
            message=validation.message,
        )

    def _from_environment(
        self,
        provider_name: ProviderName,
        env: dict[str, str | None],
        *,
        check_reachability: bool,
    ) -> ProviderDiscoveryResult:
        definition = self.registry.get(provider_name)
        keys = self.ENV_KEYS.get(provider_name, ())
        configured = any(env.get(key) for key in keys)
        base_url = str(env.get(keys[0], "") or "") if definition.is_local and keys else definition.default_base_url
        if definition.requires_api_key:
            source = "env" if configured else "none"
        else:
            base_url = base_url or definition.default_base_url
            source = "env" if configured else "none"
        reachable = self._reachable(base_url) if check_reachability and definition.is_local and base_url else False
        if definition.is_local and reachable and not configured:
            configured = True
            source = "reachable_local"
        healthy = configured and (reachable or not definition.is_local)
        return ProviderDiscoveryResult(
            provider_name=provider_name,
            status=self._status(configured=configured, reachable=reachable, healthy=healthy),
            configured=configured,
            reachable=reachable,
            healthy=healthy,
            source=source,
            model=definition.default_model,
            base_url=base_url,
            capability=self.capability_registry.get(provider_name),
            message="Detected without exposing credentials." if configured else "Provider is not configured.",
        )

    def _status(self, *, configured: bool, reachable: bool, healthy: bool) -> ProviderHealthStatus:
        if healthy:
            return ProviderHealthStatus.HEALTHY
        if reachable:
            return ProviderHealthStatus.REACHABLE
        if configured:
            return ProviderHealthStatus.CONFIGURED
        return ProviderHealthStatus.UNAVAILABLE

    def _reachable(self, base_url: str) -> bool:
        parsed = urlparse(base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.hostname:
            return False
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        try:
            with socket.create_connection((parsed.hostname, port), timeout=self.reachability_timeout_seconds):
                return True
        except OSError:
            return False
