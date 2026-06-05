from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlparse

from desktop_app.providers.provider_profile import ProviderProfile
from desktop_app.providers.provider_registry import ProviderRegistry


class ValidationStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"


@dataclass(frozen=True)
class ValidationResult:
    status: ValidationStatus
    message: str

    @property
    def is_usable(self) -> bool:
        return self.status in {ValidationStatus.HEALTHY, ValidationStatus.DEGRADED}


class ProviderValidator:
    def __init__(self, registry: ProviderRegistry | None = None) -> None:
        self.registry = registry or ProviderRegistry()

    def validate(self, profile: ProviderProfile) -> ValidationResult:
        definition = self.registry.get(profile.provider_name)
        if not profile.enabled:
            return ValidationResult(ValidationStatus.DEGRADED, "Provider is disabled.")
        if definition.requires_api_key and not profile.api_key.strip():
            return ValidationResult(ValidationStatus.FAILED, "API key is required.")
        if not profile.model.strip() and not profile.embedding_model.strip():
            return ValidationResult(ValidationStatus.FAILED, "At least one model is required.")
        if profile.base_url.strip() and not self._is_valid_url(profile.base_url):
            return ValidationResult(ValidationStatus.FAILED, "Base URL is invalid.")
        if definition.is_local and not profile.base_url.strip():
            return ValidationResult(ValidationStatus.DEGRADED, "Local provider has no base URL.")
        return ValidationResult(ValidationStatus.HEALTHY, "Provider profile is configured.")

    def _is_valid_url(self, value: str) -> bool:
        parsed = urlparse(value)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

