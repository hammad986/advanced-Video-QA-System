from __future__ import annotations

import importlib.util
import shutil
from dataclasses import dataclass


@dataclass(frozen=True)
class PackagingCheck:
    name: str
    available: bool
    detail: str


@dataclass(frozen=True)
class PackagingAuditReport:
    checks: tuple[PackagingCheck, ...]

    @property
    def blocking_issues(self) -> tuple[PackagingCheck, ...]:
        return tuple(check for check in self.checks if not check.available)

    @property
    def ready(self) -> bool:
        return not self.blocking_issues


class PackagingAuditService:
    PYTHON_MODULES: tuple[tuple[str, str], ...] = (
        ("PyInstaller", "PyInstaller"),
        ("PySide6", "PySide6"),
        ("faster-whisper", "faster_whisper"),
        ("openai-whisper", "whisper"),
        ("SentenceTransformers", "sentence_transformers"),
        ("FAISS", "faiss"),
    )

    EXECUTABLES: tuple[str, ...] = ("ffmpeg",)

    def run(self) -> PackagingAuditReport:
        checks: list[PackagingCheck] = []
        for display_name, module_name in self.PYTHON_MODULES:
            available = importlib.util.find_spec(module_name) is not None
            checks.append(
                PackagingCheck(
                    display_name,
                    available,
                    "Importable" if available else f"Python module '{module_name}' is missing.",
                )
            )
        for executable in self.EXECUTABLES:
            path = shutil.which(executable)
            checks.append(
                PackagingCheck(
                    executable,
                    path is not None,
                    path or f"Executable '{executable}' was not found on PATH.",
                )
            )
        return PackagingAuditReport(tuple(checks))
