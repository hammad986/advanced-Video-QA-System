from __future__ import annotations

import array
import time
import uuid
from dataclasses import dataclass
from enum import StrEnum


DEFAULT_EMBEDDING_MODELS: tuple[str, ...] = (
    "BAAI/bge-small-en-v1.5",
    "BAAI/bge-base-en-v1.5",
)

LARGE_EMBEDDING_MODEL = "BAAI/bge-large-en-v1.5"

OPTIONAL_EMBEDDING_MODELS: tuple[str, ...] = (
    "intfloat/e5-small-v2",
    "intfloat/e5-base-v2",
)

SUPPORTED_EMBEDDING_MODELS: tuple[str, ...] = (
    DEFAULT_EMBEDDING_MODELS + (LARGE_EMBEDDING_MODEL,) + OPTIONAL_EMBEDDING_MODELS
)

EMBEDDING_MODEL_BY_SIZE: dict[str, str] = {
    "small": DEFAULT_EMBEDDING_MODELS[0],
    "base": DEFAULT_EMBEDDING_MODELS[1],
    "large": LARGE_EMBEDDING_MODEL,
}


class EmbeddingStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class EmbeddingRecord:
    id: str
    chunk_id: str
    model_name: str
    dimension: int
    embedding_blob: bytes
    created_at: float

    @classmethod
    def create(cls, *, chunk_id: str, model_name: str, vector: list[float]) -> "EmbeddingRecord":
        return cls(
            id=str(uuid.uuid4()),
            chunk_id=chunk_id,
            model_name=model_name,
            dimension=len(vector),
            embedding_blob=serialize_vector(vector),
            created_at=time.time(),
        )

    def vector(self) -> list[float]:
        return deserialize_vector(self.embedding_blob)


@dataclass(frozen=True)
class EmbeddingJobState:
    job_id: str
    transcript_id: str
    model_name: str
    status: EmbeddingStatus
    progress_percent: int = 0
    record_count: int = 0
    error_message: str = ""


def serialize_vector(vector: list[float]) -> bytes:
    values = array.array("f", vector)
    return values.tobytes()


def deserialize_vector(blob: bytes) -> list[float]:
    values = array.array("f")
    values.frombytes(blob)
    return list(values)
