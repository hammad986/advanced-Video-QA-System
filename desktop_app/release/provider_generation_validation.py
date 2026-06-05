from __future__ import annotations

import time
from dataclasses import dataclass
from enum import StrEnum

from desktop_app.answering.answer_service import AnswerProviderError, ProviderExecutor
from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_profile import ProviderName, ProviderProfile
from desktop_app.settings.settings_manager import SettingsManager


class GenerationValidationStatus(StrEnum):
    NOT_CONFIGURED = "not_configured"
    PASSED = "passed"
    FAILED = "failed"


@dataclass(frozen=True)
class GenerationValidationResult:
    provider: ProviderName
    profile_id: str
    configured: bool
    authentication_valid: bool
    generation_valid: bool
    latency_ms: float
    response_text: str
    status: GenerationValidationStatus
    message: str

    @property
    def responded(self) -> bool:
        return self.authentication_valid and self.generation_valid


class ProviderGenerationValidationService:
    VALIDATED_PROVIDERS = (
        ProviderName.GEMINI,
        ProviderName.OPENAI,
        ProviderName.CLAUDE,
        ProviderName.GROQ,
        ProviderName.OPENROUTER,
        ProviderName.OLLAMA,
        ProviderName.LM_STUDIO,
    )
    PROMPT = "Return exactly: OK"

    def __init__(self, provider_manager: ProviderManager, settings_manager: SettingsManager) -> None:
        self.provider_manager = provider_manager
        self.settings_manager = settings_manager

    def validate_all(self) -> list[GenerationValidationResult]:
        profiles = self.provider_manager.list_providers(enabled_only=True)
        by_provider: dict[ProviderName, ProviderProfile] = {}
        for profile in profiles:
            by_provider.setdefault(profile.provider_name, profile)
        results: list[GenerationValidationResult] = []
        for provider_name in self.VALIDATED_PROVIDERS:
            profile = by_provider.get(provider_name)
            if profile is None:
                results.append(
                    GenerationValidationResult(
                        provider=provider_name,
                        profile_id="",
                        configured=False,
                        authentication_valid=False,
                        generation_valid=False,
                        latency_ms=0.0,
                        response_text="",
                        status=GenerationValidationStatus.NOT_CONFIGURED,
                        message="Provider is not configured.",
                    )
                )
                continue
            results.append(self.validate_profile(profile))
        return results

    def validate_profile(self, profile: ProviderProfile) -> GenerationValidationResult:
        original_default_provider = self.settings_manager.current.default_provider
        original_default_model = self.settings_manager.current.default_model
        started = time.perf_counter()
        try:
            self.settings_manager.update(default_provider=profile.id, default_model=profile.model)
            generation = ProviderExecutor(self.provider_manager, self.settings_manager).generate(self.PROMPT)
            latency_ms = (time.perf_counter() - started) * 1000.0
            normalized = generation.text.strip().strip('"').strip("'").strip()
            valid = normalized == "OK"
            return GenerationValidationResult(
                provider=profile.provider_name,
                profile_id=profile.id,
                configured=True,
                authentication_valid=True,
                generation_valid=valid,
                latency_ms=latency_ms,
                response_text=normalized[:100],
                status=GenerationValidationStatus.PASSED if valid else GenerationValidationStatus.FAILED,
                message="Provider generated exactly OK." if valid else "Provider responded but did not return exactly OK.",
            )
        except AnswerProviderError as error:
            latency_ms = (time.perf_counter() - started) * 1000.0
            message = str(error)
            authentication_valid = "HTTP 401" not in message and "HTTP 403" not in message
            return GenerationValidationResult(
                provider=profile.provider_name,
                profile_id=profile.id,
                configured=True,
                authentication_valid=authentication_valid,
                generation_valid=False,
                latency_ms=latency_ms,
                response_text="",
                status=GenerationValidationStatus.FAILED,
                message=message,
            )
        finally:
            self.settings_manager.update(
                default_provider=original_default_provider,
                default_model=original_default_model,
            )
