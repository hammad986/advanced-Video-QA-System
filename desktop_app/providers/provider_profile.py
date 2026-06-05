from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, replace
from enum import StrEnum


class ProviderName(StrEnum):
    GEMINI = "gemini"
    OPENAI = "openai"
    CLAUDE = "claude"
    OPENROUTER = "openrouter"
    GROQ = "groq"
    MISTRAL = "mistral"
    HUGGINGFACE = "huggingface"
    OLLAMA = "ollama"
    LM_STUDIO = "lm_studio"
    OPENAI_COMPATIBLE = "openai_compatible"


@dataclass(frozen=True)
class ProviderProfile:
    id: str
    provider_name: ProviderName
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    embedding_model: str = ""
    enabled: bool = True
    created_at: float = 0.0
    updated_at: float = 0.0

    @classmethod
    def create(
        cls,
        provider_name: ProviderName,
        *,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
        embedding_model: str = "",
        enabled: bool = True,
    ) -> "ProviderProfile":
        now = time.time()
        return cls(
            id=str(uuid.uuid4()),
            provider_name=provider_name,
            api_key=api_key,
            base_url=base_url,
            model=model,
            embedding_model=embedding_model,
            enabled=enabled,
            created_at=now,
            updated_at=now,
        )

    def with_updates(self, **changes: object) -> "ProviderProfile":
        return replace(self, updated_at=time.time(), **changes)
