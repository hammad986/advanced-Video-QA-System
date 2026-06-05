from __future__ import annotations

import os
import sys
from pathlib import Path


def configure_frozen_runtime_paths() -> None:
    _ensure_standard_streams()
    runtime_root = _runtime_root()
    candidate_roots = [
        runtime_root,
        runtime_root / "_internal",
        Path(sys.executable).resolve().parent,
        Path(sys.executable).resolve().parent / "_internal",
    ]
    for root in candidate_roots:
        _prepend_path(root)
        vendor_root = root / "_vendor_runtime"
        if vendor_root.exists():
            _prepend_sys_path(vendor_root)
            _prepend_path(vendor_root)
            for dll_path in (
                vendor_root / "torch" / "lib",
                vendor_root / "ctranslate2",
                vendor_root / "llvmlite" / "binding",
            ):
                _add_dll_directory(dll_path)
            for package_lib_dir in vendor_root.glob("*/*.libs"):
                _add_dll_directory(package_lib_dir)
            for libs_dir in vendor_root.glob("*.libs"):
                _add_dll_directory(libs_dir)
    os.environ.setdefault("TRANSFORMERS_NO_TF", "1")
    os.environ.setdefault("TRANSFORMERS_NO_FLAX", "1")
    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")


def _runtime_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))


def _prepend_sys_path(path: Path) -> None:
    if path.exists() and str(path) not in sys.path:
        sys.path.insert(0, str(path))


def _prepend_path(path: Path) -> None:
    if path.exists():
        current = os.environ.get("PATH", "")
        path_text = str(path)
        if path_text not in current.split(os.pathsep):
            os.environ["PATH"] = f"{path_text}{os.pathsep}{current}" if current else path_text


def _add_dll_directory(path: Path) -> None:
    if not path.exists():
        return
    try:
        os.add_dll_directory(str(path))
    except (AttributeError, OSError):
        _prepend_path(path)


def _ensure_standard_streams() -> None:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
