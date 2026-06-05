from __future__ import annotations

import os
import json
import logging
import traceback
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from dotenv import load_dotenv

from desktop_app.answering.answer_models import (
    INSUFFICIENT_EVIDENCE_RESPONSE,
    AnswerResult,
    ChatHistoryRecord,
)
from desktop_app.answering.answer_repository import AnswerRepository
from desktop_app.answering.citation_builder import CitationBuilder
from desktop_app.answering.context_builder import ContextBuilder
from desktop_app.evidence.evidence_service import EvidenceService
from desktop_app.providers.provider_manager import ProviderManager
from desktop_app.providers.provider_profile import ProviderName, ProviderProfile
from desktop_app.providers.provider_usage import ProviderUsageService
from desktop_app.settings.settings_manager import SettingsManager


class AnswerProviderError(RuntimeError):
    pass


class ChatPipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderGeneration:
    provider: str
    text: str
    model: str = ""
    token_usage: dict[str, int] | None = None


class ProviderExecutor:
    def __init__(self, provider_manager: ProviderManager, settings_manager: SettingsManager) -> None:
        self.provider_manager = provider_manager
        self.settings_manager = settings_manager
        load_dotenv()

    def generate(self, prompt: str) -> ProviderGeneration:
        profile = self._selected_profile()
        if profile is not None:
            return self._generate_with_profile(prompt, profile)
        return self._generate_from_environment(prompt)

    def describe_selection(self) -> tuple[str, str]:
        profile = self._selected_profile()
        if profile is not None:
            return profile.provider_name.value, profile.model
        if os.getenv("GEMINI_API_KEY"):
            return "gemini", "gemini-2.5-flash"
        if os.getenv("OPENAI_API_KEY"):
            return "openai", "gpt-4o-mini"
        if os.getenv("HF_TOKEN"):
            return "huggingface", "HuggingFaceH4/zephyr-7b-beta"
        return "", ""

    def _selected_profile(self) -> ProviderProfile | None:
        provider_id = self.settings_manager.current.default_provider
        if provider_id:
            return self.provider_manager.get_provider(provider_id)
        enabled = self.provider_manager.list_providers(enabled_only=True)
        return enabled[0] if enabled else None

    def _generate_from_environment(self, prompt: str) -> ProviderGeneration:
        if os.getenv("GEMINI_API_KEY"):
            return self._call_gemini(prompt, os.getenv("GEMINI_API_KEY", ""), "gemini-2.5-flash")
        if os.getenv("OPENAI_API_KEY"):
            return self._call_openai_compatible(
                prompt,
                provider="openai",
                api_key=os.getenv("OPENAI_API_KEY", ""),
                base_url="https://api.openai.com/v1",
                model="gpt-4o-mini",
            )
        if os.getenv("HF_TOKEN"):
            return self._call_huggingface(prompt, os.getenv("HF_TOKEN", ""), "HuggingFaceH4/zephyr-7b-beta")
        raise AnswerProviderError("No configured answer provider is available.")

    def _generate_with_profile(self, prompt: str, profile: ProviderProfile) -> ProviderGeneration:
        if profile.provider_name == ProviderName.GEMINI:
            return self._call_gemini(prompt, profile.api_key, profile.model or "gemini-2.5-flash")
        if profile.provider_name in {
            ProviderName.OPENAI,
            ProviderName.OPENROUTER,
            ProviderName.GROQ,
            ProviderName.MISTRAL,
            ProviderName.LM_STUDIO,
            ProviderName.OPENAI_COMPATIBLE,
        }:
            return self._call_openai_compatible(
                prompt,
                provider=profile.provider_name.value,
                api_key=profile.api_key,
                base_url=profile.base_url,
                model=profile.model,
            )
        if profile.provider_name == ProviderName.CLAUDE:
            return self._call_anthropic(prompt, profile.api_key, profile.base_url, profile.model)
        if profile.provider_name == ProviderName.OLLAMA:
            return self._call_ollama(prompt, profile.base_url, profile.model)
        if profile.provider_name == ProviderName.HUGGINGFACE:
            return self._call_huggingface(prompt, profile.api_key, profile.model)
        raise AnswerProviderError(f"Unsupported provider: {profile.provider_name.value}")

    def _call_gemini(self, prompt: str, api_key: str, model_name: str) -> ProviderGeneration:
        if not api_key:
            raise AnswerProviderError("Gemini API key is missing.")
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key.strip("'\" \n\r"))
            model = genai.GenerativeModel(model_name or "gemini-2.5-flash")
            response = model.generate_content(prompt)
            text = str(getattr(response, "text", "") or "").strip()
        except Exception as exc:
            raise AnswerProviderError(f"Gemini generation failed: {exc}") from exc
        if not text:
            raise AnswerProviderError("Gemini returned an empty answer.")
        usage = self._gemini_usage(response)
        return ProviderGeneration(provider="gemini", text=text, model=model_name or "gemini-2.5-flash", token_usage=usage)

    def _call_openai_compatible(
        self,
        prompt: str,
        *,
        provider: str,
        api_key: str,
        base_url: str,
        model: str,
    ) -> ProviderGeneration:
        if not base_url or not model:
            raise AnswerProviderError(f"{provider} base URL and model are required.")
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        response = requests.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
            },
            timeout=45,
        )
        if response.status_code >= 400:
            raise AnswerProviderError(_provider_http_error(provider, response.status_code))
        payload = response.json()
        text = str(payload.get("choices", [{}])[0].get("message", {}).get("content", "")).strip()
        if not text:
            raise AnswerProviderError(f"{provider} returned an empty answer.")
        return ProviderGeneration(
            provider=provider,
            text=text,
            model=model,
            token_usage=self._openai_usage(payload),
        )

    def _call_anthropic(self, prompt: str, api_key: str, base_url: str, model: str) -> ProviderGeneration:
        if not api_key:
            raise AnswerProviderError("Anthropic API key is missing.")
        response = requests.post(
            f"{(base_url or 'https://api.anthropic.com').rstrip('/')}/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model or "claude-3-5-sonnet-latest",
                "max_tokens": 800,
                "temperature": 0.0,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=45,
        )
        if response.status_code >= 400:
            raise AnswerProviderError(_provider_http_error("Anthropic", response.status_code))
        payload = response.json()
        text = "".join(part.get("text", "") for part in payload.get("content", []) if part.get("type") == "text").strip()
        if not text:
            raise AnswerProviderError("Anthropic returned an empty answer.")
        return ProviderGeneration(
            provider="anthropic",
            text=text,
            model=model or "claude-3-5-sonnet-latest",
            token_usage=self._anthropic_usage(payload),
        )

    def _call_ollama(self, prompt: str, base_url: str, model: str) -> ProviderGeneration:
        response = requests.post(
            f"{(base_url or 'http://127.0.0.1:11434').rstrip('/')}/api/generate",
            json={"model": model or "llama3.2", "prompt": prompt, "stream": False},
            timeout=60,
        )
        if response.status_code >= 400:
            raise AnswerProviderError(_provider_http_error("Ollama", response.status_code))
        text = str(response.json().get("response", "")).strip()
        if not text:
            raise AnswerProviderError("Ollama returned an empty answer.")
        return ProviderGeneration(provider="ollama", text=text, model=model or "llama3.2")

    def _call_huggingface(self, prompt: str, api_key: str, model: str) -> ProviderGeneration:
        if not api_key:
            raise AnswerProviderError("HuggingFace token is missing.")
        if not model:
            raise AnswerProviderError("HuggingFace model is required.")
        response = requests.post(
            f"https://api-inference.huggingface.co/models/{model}",
            headers={"Authorization": f"Bearer {api_key}"},
            json={"inputs": prompt, "parameters": {"max_new_tokens": 512, "temperature": 0.1}},
            timeout=60,
        )
        if response.status_code >= 400:
            raise AnswerProviderError(_provider_http_error("HuggingFace", response.status_code))
        payload = response.json()
        if isinstance(payload, list) and payload:
            text = str(payload[0].get("generated_text", "")).strip()
        else:
            text = str(payload.get("generated_text", "") if isinstance(payload, dict) else "").strip()
        if not text:
            raise AnswerProviderError("HuggingFace returned an empty answer.")
        return ProviderGeneration(provider="huggingface", text=text, model=model)

    def _gemini_usage(self, response: object) -> dict[str, int]:
        usage = getattr(response, "usage_metadata", None)
        if usage is None:
            return {}
        values: dict[str, int] = {}
        for attr, key in (
            ("prompt_token_count", "prompt_tokens"),
            ("candidates_token_count", "completion_tokens"),
            ("total_token_count", "total_tokens"),
        ):
            value = getattr(usage, attr, None)
            if isinstance(value, int):
                values[key] = value
        return values

    def _openai_usage(self, payload: dict[str, object]) -> dict[str, int]:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return {}
        values: dict[str, int] = {}
        for source, target in (
            ("prompt_tokens", "prompt_tokens"),
            ("completion_tokens", "completion_tokens"),
            ("total_tokens", "total_tokens"),
        ):
            value = usage.get(source)
            if isinstance(value, int):
                values[target] = value
        return values

    def _anthropic_usage(self, payload: dict[str, object]) -> dict[str, int]:
        usage = payload.get("usage")
        if not isinstance(usage, dict):
            return {}
        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        values: dict[str, int] = {}
        if isinstance(input_tokens, int):
            values["prompt_tokens"] = input_tokens
        if isinstance(output_tokens, int):
            values["completion_tokens"] = output_tokens
        if isinstance(input_tokens, int) and isinstance(output_tokens, int):
            values["total_tokens"] = input_tokens + output_tokens
        return values


class AnswerService:
    def __init__(
        self,
        answer_repository: AnswerRepository,
        evidence_service: EvidenceService,
        provider_executor: ProviderExecutor,
        *,
        context_builder: ContextBuilder | None = None,
        citation_builder: CitationBuilder | None = None,
        provider_usage_service: ProviderUsageService | None = None,
    ) -> None:
        self.answer_repository = answer_repository
        self.evidence_service = evidence_service
        self.provider_executor = provider_executor
        self.context_builder = context_builder or ContextBuilder()
        self.citation_builder = citation_builder or CitationBuilder()
        self.provider_usage_service = provider_usage_service

    def answer(
        self,
        *,
        project_id: str,
        question: str,
        embedding_selection: str,
        top_k: int = 5,
        min_similarity: float = 0.0,
    ) -> AnswerResult:
        started = time.perf_counter()
        provider, provider_model = _describe_provider_selection(self.provider_executor)
        retrieval_count = 0
        evidence_count = 0
        provider_latency_ms = 0.0
        _write_chat_pipeline_log(
            "chat_started",
            provider=provider,
            model=provider_model,
            query=question,
            retrieval_count=retrieval_count,
            evidence_count=evidence_count,
            provider_latency_ms=provider_latency_ms,
        )
        try:
            evidence_result = self.evidence_service.generate(
                project_id=project_id,
                query=question,
                embedding_selection=embedding_selection,
                top_k=top_k,
                min_similarity=min_similarity,
            )
            retrieval_count = int(getattr(self.evidence_service, "last_retrieval_count", len(evidence_result.items)))
            evidence_count = len(evidence_result.items)
            if retrieval_count == 0:
                raise ChatPipelineError("Retrieval returned zero evidence. Generate knowledge, embeddings, and FAISS index before asking.")
            if evidence_count == 0:
                raise ChatPipelineError("No evidence available for the retrieved chunks. Regenerate knowledge and evidence before asking.")
            context = self.context_builder.build(question=question, evidence_items=evidence_result.items)
            citations = self.citation_builder.build(context.evidence_items)
            if not context.sufficient:
                provider = "none"
                provider_model = ""
                token_usage: dict[str, int] = {}
                answer_text = INSUFFICIENT_EVIDENCE_RESPONSE
            else:
                provider_started = time.perf_counter()
                generation = self.provider_executor.generate(context.prompt_context)
                provider_latency_ms = (time.perf_counter() - provider_started) * 1000
                provider = generation.provider
                provider_model = generation.model
                token_usage = generation.token_usage or {}
                answer_text = self.citation_builder.append_citation_block(generation.text, citations)
            duration_ms = (time.perf_counter() - started) * 1000
            self.answer_repository.save_chat(
                ChatHistoryRecord.create(
                    project_id=project_id,
                    question=question,
                    answer=answer_text,
                    citations_json=self.citation_builder.to_json(citations),
                    provider=provider,
                    duration_ms=duration_ms,
                )
            )
            if self.provider_usage_service is not None and provider != "none":
                self.provider_usage_service.record(
                    project_id=project_id,
                    provider=provider,
                    model=provider_model,
                    task_type="answer_generation",
                    token_usage=token_usage,
                    response_time_ms=duration_ms,
                )
            _write_chat_pipeline_log(
                "chat_completed",
                provider=provider,
                model=provider_model,
                query=question,
                retrieval_count=retrieval_count,
                evidence_count=evidence_count,
                provider_latency_ms=provider_latency_ms,
                duration_ms=duration_ms,
            )
            return AnswerResult(
                project_id=project_id,
                question=question,
                answer=answer_text,
                provider=provider,
                citations=citations,
                evidence_items=context.evidence_items,
                duration_ms=duration_ms,
                created_at=time.time(),
                provider_model=provider_model,
                token_usage=token_usage,
            )
        except Exception as exc:
            actionable = _actionable_chat_error(exc)
            _write_chat_pipeline_log(
                "chat_failed",
                provider=provider,
                model=provider_model,
                query=question,
                retrieval_count=retrieval_count,
                evidence_count=evidence_count,
                provider_latency_ms=provider_latency_ms,
                exception_type=exc.__class__.__name__,
                exception_message=str(exc),
                actionable_error=actionable,
                traceback=traceback.format_exc(),
            )
            if isinstance(exc, ChatPipelineError):
                raise
            raise ChatPipelineError(actionable) from exc


def _describe_provider_selection(provider_executor: object) -> tuple[str, str]:
    describe = getattr(provider_executor, "describe_selection", None)
    if callable(describe):
        provider, model = describe()
        return str(provider or ""), str(model or "")
    return "", ""


def _provider_http_error(provider: str, status_code: int) -> str:
    if status_code in {401, 403}:
        return f"Invalid API key for {provider} (HTTP {status_code})."
    if status_code == 429:
        return f"Provider quota exceeded for {provider} (HTTP 429)."
    if status_code in {408, 504}:
        return f"Network timeout while contacting {provider} (HTTP {status_code})."
    return f"{provider} generation failed with HTTP {status_code}."


def _actionable_chat_error(exc: Exception) -> str:
    text = str(exc).strip()
    lowered = text.lower()
    if isinstance(exc, requests.exceptions.Timeout) or "timeout" in lowered or "timed out" in lowered:
        return f"Network timeout: {text or 'provider did not respond before the request timeout.'}"
    if "no configured answer provider" in lowered:
        return "No provider configured. Enable a provider or add a provider API key before asking."
    if "api key" in lowered and ("invalid" in lowered or "missing" in lowered or "authentication" in lowered):
        return text
    if "quota" in lowered or "http 429" in lowered or "rate limit" in lowered:
        return text if text else "Provider quota exceeded."
    if "no faiss index" in lowered or "faiss index does not exist" in lowered:
        return f"No FAISS index available. Build embeddings and the FAISS index before asking. Details: {text}"
    if "no embeddings" in lowered or "no embeddings are available" in lowered:
        return f"No embeddings available. Generate embeddings before asking. Details: {text}"
    if "knowledge" in lowered and ("no " in lowered or "missing" in lowered):
        return f"No knowledge generated. Generate knowledge chunks before asking. Details: {text}"
    if "retrieval returned zero evidence" in lowered:
        return text
    if isinstance(exc, ChatPipelineError):
        return text
    if text:
        return f"Internal exception: {exc.__class__.__name__}: {text}"
    return f"Internal exception: {exc.__class__.__name__}"


def _write_chat_pipeline_log(event: str, **fields: object) -> None:
    record = {"event": event, "created_at": time.time(), **fields}
    log_path = Path("logs") / "chat_pipeline.log"
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True, default=str) + "\n")
    except OSError:
        logging.getLogger(__name__).exception("Unable to write chat pipeline log")
