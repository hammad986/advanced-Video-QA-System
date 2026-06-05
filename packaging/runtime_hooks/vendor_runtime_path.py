from __future__ import annotations

import os
import sys
from pathlib import Path

from desktop_app.core.frozen_runtime import configure_frozen_runtime_paths


def _runtime_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))


def _add_dll_directory(path: Path) -> None:
    if not path.exists():
        return
    try:
        os.add_dll_directory(str(path))
    except (AttributeError, OSError):
        os.environ["PATH"] = f"{path}{os.pathsep}{os.environ.get('PATH', '')}"


runtime_root = _runtime_root()
os.environ["PATH"] = f"{runtime_root}{os.pathsep}{os.environ.get('PATH', '')}"
vendor_root = runtime_root / "_vendor_runtime"
for libs_dir in runtime_root.glob("*.libs"):
    _add_dll_directory(libs_dir)
if vendor_root.exists():
    sys.path.insert(0, str(vendor_root))
    _add_dll_directory(vendor_root)
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
configure_frozen_runtime_paths()
