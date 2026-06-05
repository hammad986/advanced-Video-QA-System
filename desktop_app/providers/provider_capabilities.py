from __future__ import annotations

from dataclasses import dataclass

from desktop_app.providers.provider_profile import ProviderName


@dataclass(frozen=True)
class ProviderCapability:
    provider_name: ProviderName
    is_local: bool
    context_window: int
    estimated_latency_ms: float
    estimated_cost_per_1k_tokens: float
    supports_multimodal: bool
    supports_reasoning: bool
    supports_streaming: bool


class ProviderCapabilityRegistry:
    def __init__(self) -> None:
        self._capabilities: dict[ProviderName, ProviderCapability] = {
            ProviderName.GEMINI: ProviderCapability(
                provider_name=ProviderName.GEMINI,
                is_local=False,
                context_window=1_000_000,
                estimated_latency_ms=1800,
                estimated_cost_per_1k_tokens=0.00025,
                supports_multimodal=True,
                supports_reasoning=True,
                supports_streaming=True,
            ),
            ProviderName.OPENAI: ProviderCapability(
                provider_name=ProviderName.OPENAI,
                is_local=False,
                context_window=128_000,
                estimated_latency_ms=1600,
                estimated_cost_per_1k_tokens=0.00060,
                supports_multimodal=True,
                supports_reasoning=True,
                supports_streaming=True,
            ),
            ProviderName.CLAUDE: ProviderCapability(
                provider_name=ProviderName.CLAUDE,
                is_local=False,
                context_window=200_000,
                estimated_latency_ms=2200,
                estimated_cost_per_1k_tokens=0.00080,
                supports_multimodal=True,
                supports_reasoning=True,
                supports_streaming=True,
            ),
            ProviderName.GROQ: ProviderCapability(
                provider_name=ProviderName.GROQ,
                is_local=False,
                context_window=32_000,
                estimated_latency_ms=450,
                estimated_cost_per_1k_tokens=0.00020,
                supports_multimodal=False,
                supports_reasoning=False,
                supports_streaming=True,
            ),
            ProviderName.OPENROUTER: ProviderCapability(
                provider_name=ProviderName.OPENROUTER,
                is_local=False,
                context_window=128_000,
                estimated_latency_ms=1900,
                estimated_cost_per_1k_tokens=0.00050,
                supports_multimodal=True,
                supports_reasoning=True,
                supports_streaming=True,
            ),
            ProviderName.MISTRAL: ProviderCapability(
                provider_name=ProviderName.MISTRAL,
                is_local=False,
                context_window=128_000,
                estimated_latency_ms=1400,
                estimated_cost_per_1k_tokens=0.00040,
                supports_multimodal=False,
                supports_reasoning=True,
                supports_streaming=True,
            ),
            ProviderName.HUGGINGFACE: ProviderCapability(
                provider_name=ProviderName.HUGGINGFACE,
                is_local=False,
                context_window=32_000,
                estimated_latency_ms=2500,
                estimated_cost_per_1k_tokens=0.00010,
                supports_multimodal=False,
                supports_reasoning=False,
                supports_streaming=False,
            ),
            ProviderName.OLLAMA: ProviderCapability(
                provider_name=ProviderName.OLLAMA,
                is_local=True,
                context_window=32_000,
                estimated_latency_ms=1200,
                estimated_cost_per_1k_tokens=0.0,
                supports_multimodal=False,
                supports_reasoning=False,
                supports_streaming=True,
            ),
            ProviderName.LM_STUDIO: ProviderCapability(
                provider_name=ProviderName.LM_STUDIO,
                is_local=True,
                context_window=32_000,
                estimated_latency_ms=1000,
                estimated_cost_per_1k_tokens=0.0,
                supports_multimodal=False,
                supports_reasoning=False,
                supports_streaming=True,
            ),
            ProviderName.OPENAI_COMPATIBLE: ProviderCapability(
                provider_name=ProviderName.OPENAI_COMPATIBLE,
                is_local=True,
                context_window=64_000,
                estimated_latency_ms=1000,
                estimated_cost_per_1k_tokens=0.0,
                supports_multimodal=False,
                supports_reasoning=False,
                supports_streaming=True,
            ),
        }

    def get(self, provider_name: ProviderName) -> ProviderCapability:
        return self._capabilities[provider_name]

    def all(self) -> list[ProviderCapability]:
        return list(self._capabilities.values())

