from __future__ import annotations

import gc
import threading
import time
from contextlib import nullcontext
from typing import Any

from desktop_app.embeddings.embedding_worker import EmbeddingModelUnavailable


class EmbeddingModelRegistry:
    _global_instance: "EmbeddingModelRegistry | None" = None
    _global_lock = threading.Lock()

    def __init__(self) -> None:
        self._models: dict[str, object] = {}
        self._last_used: dict[str, float] = {}
        self._idle_timeout_seconds = 600.0
        self._lock = threading.RLock()

    @classmethod
    def global_instance(cls) -> "EmbeddingModelRegistry":
        with cls._global_lock:
            if cls._global_instance is None:
                cls._global_instance = cls()
            return cls._global_instance

    def get_model(self, model_name: str) -> object:
        with self._lock:
            if model_name in self._models:
                self._last_used[model_name] = time.monotonic()
                return self._models[model_name]
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError as exc:
                raise EmbeddingModelUnavailable(
                    "sentence-transformers is required for local BGE embeddings."
                ) from exc
            model = SentenceTransformer(model_name)
            self._models[model_name] = model
            self._last_used[model_name] = time.monotonic()
            return model

    def encode(self, text_or_texts: str | list[str], model_name: str, *, batch_size: int = 32) -> Any:
        with self._lock:
            model = self.get_model(model_name)
            context = self._torch_no_grad_context()
            with context:
                result = model.encode(
                    text_or_texts,
                    batch_size=max(1, batch_size),
                    normalize_embeddings=True,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                )
            self._last_used[model_name] = time.monotonic()
            return result

    def loaded_model_count(self) -> int:
        with self._lock:
            return len(self._models)

    def loaded_model_names(self) -> list[str]:
        with self._lock:
            return sorted(self._models)

    def set_idle_timeout(self, seconds: float) -> None:
        with self._lock:
            self._idle_timeout_seconds = max(0.0, seconds)

    def unload_model(self, model_name: str) -> bool:
        with self._lock:
            existed = model_name in self._models
            self._models.pop(model_name, None)
            self._last_used.pop(model_name, None)
        if existed:
            self._cleanup_memory()
        return existed

    def unload_idle_models(self, *, force: bool = False) -> list[str]:
        now = time.monotonic()
        with self._lock:
            if force:
                stale = list(self._models)
            else:
                stale = [
                    model_name
                    for model_name in self._models
                    if now - self._last_used.get(model_name, now) >= self._idle_timeout_seconds
                ]
            for model_name in stale:
                self._models.pop(model_name, None)
                self._last_used.pop(model_name, None)
        if stale:
            self._cleanup_memory()
        return stale

    def estimated_model_memory_mb(self) -> float:
        estimates = {
            "BAAI/bge-small-en-v1.5": 135.0,
            "BAAI/bge-base-en-v1.5": 420.0,
            "BAAI/bge-large-en-v1.5": 1300.0,
            "intfloat/e5-small-v2": 135.0,
            "intfloat/e5-base-v2": 420.0,
        }
        with self._lock:
            return sum(estimates.get(model_name, 250.0) for model_name in self._models)

    def clear(self) -> None:
        with self._lock:
            self._models.clear()
            self._last_used.clear()
        self._cleanup_memory()

    def _cleanup_memory(self) -> None:
        gc.collect()
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    def _torch_no_grad_context(self):
        try:
            import torch
        except Exception:
            return nullcontext()
        return torch.no_grad()
