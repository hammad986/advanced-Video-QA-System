from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from desktop_app.performance.hardware_profiles import HardwareProfile, HardwareProfileDetector


class RuntimeProfileName(StrEnum):
    LOW_MEMORY = "low_memory"
    BALANCED = "balanced"
    PERFORMANCE = "performance"
    AUTOMATIC = "automatic"


@dataclass(frozen=True)
class RuntimeProfile:
    name: RuntimeProfileName
    worker_strategy: str
    embedding_selection: str
    embedding_model: str
    whisper_model: str
    embedding_batch_size: int
    cache_policy: str
    keep_retrieval_warm: bool
    keep_embedding_warm: bool
    keep_transcription_warm: bool
    reason: str
    hardware_profile: HardwareProfile


class RuntimeProfileManager:
    def __init__(self, detector: HardwareProfileDetector | None = None) -> None:
        self.detector = detector or HardwareProfileDetector()

    def resolve(self, requested: str = "automatic") -> RuntimeProfile:
        hardware = self.detector.detect()
        profile_name = self._profile_name(requested, hardware)
        if profile_name == RuntimeProfileName.LOW_MEMORY:
            return RuntimeProfile(
                name=profile_name,
                worker_strategy="starter",
                embedding_selection="small",
                embedding_model="BAAI/bge-small-en-v1.5",
                whisper_model="tiny",
                embedding_batch_size=4,
                cache_policy="aggressive_unload",
                keep_retrieval_warm=True,
                keep_embedding_warm=True,
                keep_transcription_warm=True,
                reason="Low memory profile minimizes UI RAM and uses small local models.",
                hardware_profile=hardware,
            )
        if profile_name == RuntimeProfileName.PERFORMANCE:
            return RuntimeProfile(
                name=profile_name,
                worker_strategy="workstation" if hardware.ram_gb >= 48 else "advanced",
                embedding_selection="large" if hardware.ram_gb >= 24 else "base",
                embedding_model="BAAI/bge-large-en-v1.5" if hardware.ram_gb >= 24 else "BAAI/bge-base-en-v1.5",
                whisper_model="large" if hardware.ram_gb >= 48 else "medium",
                embedding_batch_size=32 if hardware.ram_gb >= 48 else 16,
                cache_policy="keep_warm",
                keep_retrieval_warm=True,
                keep_embedding_warm=True,
                keep_transcription_warm=hardware.ram_gb >= 48,
                reason="Performance profile keeps heavy workers warm for faster research workflows.",
                hardware_profile=hardware,
            )
        return RuntimeProfile(
            name=profile_name,
            worker_strategy="standard" if hardware.ram_gb < 24 else "advanced",
            embedding_selection="base" if hardware.ram_gb >= 12 else "small",
            embedding_model="BAAI/bge-base-en-v1.5" if hardware.ram_gb >= 12 else "BAAI/bge-small-en-v1.5",
            whisper_model="small" if hardware.ram_gb >= 12 else "tiny",
            embedding_batch_size=8 if hardware.ram_gb < 24 else 16,
            cache_policy="warm_retrieval",
            keep_retrieval_warm=True,
            keep_embedding_warm=hardware.ram_gb >= 24,
            keep_transcription_warm=False,
            reason="Balanced profile preserves responsiveness while warming the highest-frequency retrieval path.",
            hardware_profile=hardware,
        )

    def _profile_name(self, requested: str, hardware: HardwareProfile) -> RuntimeProfileName:
        normalized = requested.strip().lower() or RuntimeProfileName.AUTOMATIC.value
        if normalized in {"low_memory", "low memory", "starter"}:
            return RuntimeProfileName.LOW_MEMORY
        if normalized in {"performance", "fast"}:
            return RuntimeProfileName.PERFORMANCE
        if normalized in {"balanced", "quality"}:
            return RuntimeProfileName.BALANCED
        if hardware.ram_gb < 12:
            return RuntimeProfileName.LOW_MEMORY
        if hardware.ram_gb >= 32:
            return RuntimeProfileName.PERFORMANCE
        return RuntimeProfileName.BALANCED

