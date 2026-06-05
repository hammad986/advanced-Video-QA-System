from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ProviderRouteKind(StrEnum):
    LOCAL = "local"
    GEMINI = "gemini"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GROQ = "groq"
    OPENROUTER = "openrouter"
    MISTRAL = "mistral"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass(frozen=True)
class ProviderRoute:
    kind: ProviderRouteKind
    provider_id: str
    model_name: str
    reason: str


class ProviderRouter:
    def smart_route(
        self,
        *,
        query: str,
        task_type: str = "answering",
        manual_override: str = "",
        available_providers: set[str] | None = None,
        local_available: bool = True,
    ) -> ProviderRoute:
        available = {provider.lower() for provider in (available_providers or set())}
        override = manual_override.strip().lower()
        if override:
            return self.route(
                task_type=task_type,
                preferred_provider=override,
                local_available=local_available,
            )
        intent = self.classify_query(query)
        ordered = self._ordered_candidates(intent)
        for provider in ordered:
            if provider == ProviderRouteKind.LOCAL.value and local_available:
                return ProviderRoute(
                    kind=ProviderRouteKind.LOCAL,
                    provider_id="local",
                    model_name="",
                    reason=f"{intent} query routed to local/fastest path.",
                )
            if provider in available:
                return ProviderRoute(
                    kind=ProviderRouteKind(provider),
                    provider_id=provider,
                    model_name="",
                    reason=f"{intent} query routed to {provider}.",
                )
        return ProviderRoute(
            kind=ProviderRouteKind.OPENROUTER,
            provider_id="openrouter",
            model_name="",
            reason=f"{intent} query fell back to OpenRouter.",
        )

    def classify_query(self, query: str) -> str:
        text = query.strip().lower()
        word_count = len(text.split())
        synthesis_terms = {"synthesize", "comprehensive", "report", "summarize all", "long", "essay"}
        research_terms = {"research", "compare", "evidence", "citations", "contradiction", "findings"}
        fast_terms = {"quick", "fast", "brief", "one sentence", "tl;dr"}
        if any(term in text for term in fast_terms):
            return "fast_response"
        if any(term in text for term in synthesis_terms) or word_count > 80:
            return "long_synthesis"
        if any(term in text for term in research_terms):
            return "research"
        return "simple"

    def _ordered_candidates(self, intent: str) -> list[str]:
        if intent == "simple":
            return [ProviderRouteKind.LOCAL.value, ProviderRouteKind.GROQ.value, ProviderRouteKind.OPENAI.value]
        if intent == "research":
            return [ProviderRouteKind.GEMINI.value, ProviderRouteKind.OPENAI.value, ProviderRouteKind.OPENROUTER.value]
        if intent == "long_synthesis":
            return [ProviderRouteKind.OPENAI.value, ProviderRouteKind.GEMINI.value, ProviderRouteKind.OPENROUTER.value]
        if intent == "fast_response":
            return [ProviderRouteKind.GROQ.value, ProviderRouteKind.LOCAL.value, ProviderRouteKind.OPENROUTER.value]
        return [ProviderRouteKind.OPENROUTER.value]

    def route(
        self,
        *,
        task_type: str,
        preferred_provider: str = "",
        preferred_model: str = "",
        local_available: bool = True,
    ) -> ProviderRoute:
        normalized = preferred_provider.strip().lower()
        if normalized == "claude":
            normalized = ProviderRouteKind.ANTHROPIC.value
        if normalized in {item.value for item in ProviderRouteKind if item is not ProviderRouteKind.LOCAL}:
            return ProviderRoute(
                kind=ProviderRouteKind(normalized),
                provider_id=normalized,
                model_name=preferred_model,
                reason=f"User selected {normalized} for {task_type}.",
            )
        if local_available:
            return ProviderRoute(
                kind=ProviderRouteKind.LOCAL,
                provider_id="local",
                model_name=preferred_model,
                reason=f"Local route selected for {task_type}.",
            )
        return ProviderRoute(
            kind=ProviderRouteKind.OPENAI,
            provider_id="openai",
            model_name=preferred_model,
            reason=f"Fallback cloud route selected for {task_type}.",
        )
