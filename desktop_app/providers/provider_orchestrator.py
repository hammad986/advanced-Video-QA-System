from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from desktop_app.providers.provider_benchmark import ProviderBenchmarkRepository
from desktop_app.providers.provider_capabilities import ProviderCapabilityRegistry
from desktop_app.providers.provider_discovery import ProviderDiscoveryResult
from desktop_app.providers.provider_profile import ProviderName
from desktop_app.providers.provider_router import ProviderRoute, ProviderRouteKind


class ProviderRoutingMode(StrEnum):
    AUTOMATIC = "automatic"
    LOCAL_FIRST = "local_first"
    MANUAL = "manual"
    PRIVACY = "privacy"
    COST = "cost"
    LATENCY = "latency"


@dataclass(frozen=True)
class ProviderRoutingRequest:
    query: str
    task_type: str
    mode: ProviderRoutingMode = ProviderRoutingMode.AUTOMATIC
    manual_provider: str = ""
    required_context_window: int = 0
    requires_multimodal: bool = False
    requires_reasoning: bool = False
    allow_cloud: bool = True


@dataclass(frozen=True)
class ProviderCandidateScore:
    provider_name: ProviderName
    provider_id: str
    model: str
    score: float
    reasons: list[str]


class ProviderOrchestrationEngine:
    LOCAL_PRIORITY = (ProviderName.OLLAMA, ProviderName.LM_STUDIO, ProviderName.OPENAI_COMPATIBLE)

    def __init__(
        self,
        *,
        capability_registry: ProviderCapabilityRegistry | None = None,
        benchmark_repository: ProviderBenchmarkRepository | None = None,
    ) -> None:
        self.capability_registry = capability_registry or ProviderCapabilityRegistry()
        self.benchmark_repository = benchmark_repository

    def route(
        self,
        *,
        providers: list[ProviderDiscoveryResult],
        request: ProviderRoutingRequest,
    ) -> ProviderRoute:
        usable = [provider for provider in providers if provider.usable]
        if request.manual_provider:
            manual = self._find_provider(usable, request.manual_provider)
            if manual is not None:
                return self._route_from_result(manual, f"Manual provider override selected {manual.provider_name.value}.")
        if not usable:
            return ProviderRoute(
                kind=ProviderRouteKind.OPENROUTER,
                provider_id="openrouter",
                model_name="",
                reason="No configured providers were usable; OpenRouter fallback selected.",
            )
        if len(usable) == 1:
            only = usable[0]
            return self._route_from_result(only, f"Single provider mode: using {only.provider_name.value} for everything.")
        if request.mode == ProviderRoutingMode.LOCAL_FIRST or not request.allow_cloud:
            local = self._first_local_provider(usable)
            if local is not None and self._supports(local, request):
                return self._route_from_result(local, f"Local First selected {local.provider_name.value}.")
            if not request.allow_cloud:
                return self._route_from_result(usable[0], "Cloud disabled; using first configured local-compatible provider.")
        scores = [self._score(provider, request) for provider in usable if self._supports(provider, request)]
        if not scores:
            scores = [self._score(provider, request, ignore_capability_gap=True) for provider in usable]
        winner = max(scores, key=lambda item: item.score)
        return ProviderRoute(
            kind=self._route_kind(winner.provider_name),
            provider_id=winner.provider_id,
            model_name=winner.model,
            reason="; ".join(winner.reasons),
        )

    def _score(
        self,
        provider: ProviderDiscoveryResult,
        request: ProviderRoutingRequest,
        *,
        ignore_capability_gap: bool = False,
    ) -> ProviderCandidateScore:
        capability = provider.capability or self.capability_registry.get(provider.provider_name)
        score = 0.0
        reasons: list[str] = []
        if capability.is_local:
            score += 25
            reasons.append("privacy/local provider")
        if request.mode == ProviderRoutingMode.COST:
            score += max(0.0, 25 - (capability.estimated_cost_per_1k_tokens * 20_000))
            reasons.append("cost-prioritized")
        else:
            score += max(0.0, 15 - (capability.estimated_cost_per_1k_tokens * 10_000))
        if request.mode == ProviderRoutingMode.LATENCY or self._intent(request.query, request.task_type) == "fast_response":
            score += max(0.0, 30 - (capability.estimated_latency_ms / 100))
            reasons.append("latency-prioritized")
        else:
            score += max(0.0, 15 - (capability.estimated_latency_ms / 200))
        required_context = request.required_context_window or self._required_context_window(request)
        if capability.context_window >= required_context:
            score += 20
            reasons.append(f"context window >= {required_context}")
        elif not ignore_capability_gap:
            score -= 100
        if request.requires_multimodal and capability.supports_multimodal:
            score += 15
            reasons.append("multimodal capable")
        if request.requires_reasoning and capability.supports_reasoning:
            score += 15
            reasons.append("reasoning capable")
        if capability.supports_streaming:
            score += 5
        benchmark = self.benchmark_repository.summarize(provider=provider.provider_name.value, task_type=request.task_type) if self.benchmark_repository else None
        if benchmark and benchmark.samples:
            score += benchmark.success_rate * 20
            score -= benchmark.failure_rate * 30
            score += max(0.0, 10 - (benchmark.average_latency_ms / 500))
            reasons.append(f"historical success {benchmark.success_rate:.2f}")
        intent = self._intent(request.query, request.task_type)
        score += self._intent_bonus(provider.provider_name, intent)
        reasons.append(f"intent={intent}")
        return ProviderCandidateScore(
            provider_name=provider.provider_name,
            provider_id=provider.profile_id or provider.provider_name.value,
            model=provider.model,
            score=score,
            reasons=reasons,
        )

    def _supports(self, provider: ProviderDiscoveryResult, request: ProviderRoutingRequest) -> bool:
        capability = provider.capability or self.capability_registry.get(provider.provider_name)
        required_context = request.required_context_window or self._required_context_window(request)
        if capability.context_window < required_context:
            return False
        if request.requires_multimodal and not capability.supports_multimodal:
            return False
        if request.requires_reasoning and not capability.supports_reasoning:
            return False
        if not request.allow_cloud and not capability.is_local:
            return False
        return True

    def _required_context_window(self, request: ProviderRoutingRequest) -> int:
        intent = self._intent(request.query, request.task_type)
        if request.task_type in {"multi_video_compare", "large_context"} or intent in {"long_synthesis", "large_context"}:
            return 128_000
        if intent == "research":
            return 64_000
        return 8_000

    def _intent(self, query: str, task_type: str) -> str:
        text = query.strip().lower()
        if task_type in {"multi_video_compare", "compare"}:
            return "multi_video_compare"
        if task_type == "large_context":
            return "large_context"
        if any(term in text for term in {"quick", "fast", "brief", "tl;dr"}):
            return "fast_response"
        if any(term in text for term in {"comprehensive", "synthesis", "report", "summarize all"}) or len(text.split()) > 80:
            return "long_synthesis"
        if any(term in text for term in {"research", "evidence", "citation", "contradiction", "compare"}):
            return "research"
        return "simple"

    def _intent_bonus(self, provider_name: ProviderName, intent: str) -> float:
        if intent == "simple" and provider_name in {ProviderName.OLLAMA, ProviderName.LM_STUDIO, ProviderName.GROQ}:
            return 15
        if intent == "research" and provider_name == ProviderName.GEMINI:
            return 25
        if intent == "long_synthesis" and provider_name in {ProviderName.OPENAI, ProviderName.CLAUDE}:
            return 25
        if intent == "fast_response" and provider_name == ProviderName.GROQ:
            return 30
        if intent in {"multi_video_compare", "large_context"} and provider_name in {ProviderName.GEMINI, ProviderName.OPENAI, ProviderName.CLAUDE}:
            return 25
        return 0

    def _first_local_provider(self, providers: list[ProviderDiscoveryResult]) -> ProviderDiscoveryResult | None:
        by_name = {provider.provider_name: provider for provider in providers}
        for name in self.LOCAL_PRIORITY:
            if name in by_name:
                return by_name[name]
        return next((provider for provider in providers if provider.capability and provider.capability.is_local), None)

    def _find_provider(self, providers: list[ProviderDiscoveryResult], provider_name: str) -> ProviderDiscoveryResult | None:
        normalized = provider_name.strip().lower()
        return next(
            (
                provider
                for provider in providers
                if provider.provider_name.value == normalized or provider.profile_id == normalized
            ),
            None,
        )

    def _route_from_result(self, provider: ProviderDiscoveryResult, reason: str) -> ProviderRoute:
        return ProviderRoute(
            kind=self._route_kind(provider.provider_name),
            provider_id=provider.profile_id or provider.provider_name.value,
            model_name=provider.model,
            reason=reason,
        )

    def _route_kind(self, provider_name: ProviderName) -> ProviderRouteKind:
        if provider_name == ProviderName.CLAUDE:
            return ProviderRouteKind.ANTHROPIC
        return ProviderRouteKind(provider_name.value)
