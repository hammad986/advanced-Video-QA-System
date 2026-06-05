from __future__ import annotations

from dataclasses import dataclass

from desktop_app.providers.provider_profile import ProviderName


@dataclass(frozen=True)
class ProviderDefinition:
    name: ProviderName
    display_name: str
    default_base_url: str
    default_model: str
    default_embedding_model: str
    requires_api_key: bool
    supports_embeddings: bool
    is_local: bool


class ProviderRegistry:
    def __init__(self) -> None:
        self._definitions: dict[ProviderName, ProviderDefinition] = {
            ProviderName.GEMINI: ProviderDefinition(
                ProviderName.GEMINI,
                "Gemini",
                "https://generativelanguage.googleapis.com",
                "gemini-2.5-flash",
                "text-embedding-004",
                True,
                True,
                False,
            ),
            ProviderName.OPENAI: ProviderDefinition(
                ProviderName.OPENAI,
                "OpenAI",
                "https://api.openai.com/v1",
                "gpt-4o-mini",
                "text-embedding-3-small",
                True,
                True,
                False,
            ),
            ProviderName.CLAUDE: ProviderDefinition(
                ProviderName.CLAUDE,
                "Claude",
                "https://api.anthropic.com",
                "claude-3-5-sonnet-latest",
                "",
                True,
                False,
                False,
            ),
            ProviderName.OPENROUTER: ProviderDefinition(
                ProviderName.OPENROUTER,
                "OpenRouter",
                "https://openrouter.ai/api/v1",
                "openai/gpt-4o-mini",
                "",
                True,
                False,
                False,
            ),
            ProviderName.GROQ: ProviderDefinition(
                ProviderName.GROQ,
                "Groq",
                "https://api.groq.com/openai/v1",
                "llama-3.1-8b-instant",
                "",
                True,
                False,
                False,
            ),
            ProviderName.MISTRAL: ProviderDefinition(
                ProviderName.MISTRAL,
                "Mistral",
                "https://api.mistral.ai/v1",
                "mistral-small-latest",
                "",
                True,
                False,
                False,
            ),
            ProviderName.HUGGINGFACE: ProviderDefinition(
                ProviderName.HUGGINGFACE,
                "HuggingFace",
                "https://api-inference.huggingface.co",
                "HuggingFaceH4/zephyr-7b-beta",
                "sentence-transformers/all-MiniLM-L6-v2",
                True,
                True,
                False,
            ),
            ProviderName.OLLAMA: ProviderDefinition(
                ProviderName.OLLAMA,
                "Ollama",
                "http://127.0.0.1:11434",
                "llama3.2",
                "nomic-embed-text",
                False,
                True,
                True,
            ),
            ProviderName.LM_STUDIO: ProviderDefinition(
                ProviderName.LM_STUDIO,
                "LM Studio",
                "http://127.0.0.1:1234/v1",
                "local-model",
                "",
                False,
                False,
                True,
            ),
            ProviderName.OPENAI_COMPATIBLE: ProviderDefinition(
                ProviderName.OPENAI_COMPATIBLE,
                "OpenAI-Compatible",
                "http://127.0.0.1:8000/v1",
                "local-model",
                "",
                False,
                False,
                True,
            ),
        }

    def all(self) -> list[ProviderDefinition]:
        return list(self._definitions.values())

    def get(self, provider_name: ProviderName) -> ProviderDefinition:
        return self._definitions[provider_name]

    def display_name(self, provider_name: ProviderName) -> str:
        return self.get(provider_name).display_name
