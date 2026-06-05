# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
from importlib import metadata
import importlib.util


block_cipher = None
ROOT = Path(SPECPATH).parent

hiddenimports = [
    "google.generativeai",
]

datas = [
    (str(ROOT / "desktop_app" / "resources"), "desktop_app/resources"),
    (str(ROOT / ".env.example"), "."),
]

binaries = []


def _vendor_module(module_name):
    spec = importlib.util.find_spec(module_name)
    if spec is None or not spec.submodule_search_locations:
        return []
    source = Path(next(iter(spec.submodule_search_locations)))
    destination = Path("_vendor_runtime") / Path(*module_name.split("."))
    return [(str(source), str(destination))]


def _vendor_distribution(distribution_name):
    try:
        distribution = metadata.distribution(distribution_name)
    except metadata.PackageNotFoundError:
        return []
    dist_path = Path(distribution._path)  # type: ignore[attr-defined]
    if not dist_path.exists():
        return []
    return [(str(dist_path), f"_vendor_runtime/{dist_path.name}")]


def _vendor_adjacent_libs(distribution_name):
    try:
        distribution = metadata.distribution(distribution_name)
    except metadata.PackageNotFoundError:
        return []
    site_packages = Path(distribution._path).parent  # type: ignore[attr-defined]
    normalized = distribution_name.replace("-", "_")
    results = []
    for libs_dir in site_packages.glob(f"{normalized}*.libs"):
        if libs_dir.is_dir():
            results.append((str(libs_dir), f"_vendor_runtime/{libs_dir.name}"))
    return results


def _optional_binary(path_text, target_dir="."):
    path = Path(path_text)
    if not path.exists():
        return []
    return [(str(path), target_dir)]


vendor_modules = [
    "torch",
    "torchgen",
    "transformers",
    "sentence_transformers",
    "faster_whisper",
    "whisper",
    "faiss",
    "scipy",
    "numba",
    "llvmlite",
    "sklearn",
    "tokenizers",
    "safetensors",
    "huggingface_hub",
    "ctranslate2",
    "av",
    "onnxruntime",
    "joblib",
    "threadpoolctl",
    "regex",
    "tiktoken",
    "tiktoken_ext",
    "tqdm",
    "httpx",
    "httpcore",
    "anyio",
    "certifi",
    "h11",
    "idna",
    "sniffio",
]

vendor_distributions = [
    "torch",
    "transformers",
    "sentence-transformers",
    "faster-whisper",
    "openai-whisper",
    "faiss-cpu",
    "scipy",
    "numba",
    "llvmlite",
    "scikit-learn",
    "tokenizers",
    "safetensors",
    "huggingface-hub",
    "ctranslate2",
    "av",
    "onnxruntime",
    "joblib",
    "threadpoolctl",
    "regex",
    "tiktoken",
    "tqdm",
    "httpx",
    "httpcore",
    "anyio",
    "certifi",
    "h11",
    "idna",
    "sniffio",
]

for module_name in vendor_modules:
    datas += _vendor_module(module_name)
for distribution_name in vendor_distributions:
    datas += _vendor_distribution(distribution_name)
    datas += _vendor_adjacent_libs(distribution_name)

binaries += _optional_binary(r"C:\Program Files\ffmpeg\bin\ffmpeg.exe")
binaries += _optional_binary(r"C:\Program Files\ffmpeg\bin\ffprobe.exe")


a = Analysis(
    [str(ROOT / "desktop_app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(ROOT / "packaging" / "runtime_hooks" / "vendor_runtime_path.py")],
    excludes=[
        "torch",
        "torchaudio",
        "torchvision",
        "transformers",
        "sentence_transformers",
        "faster_whisper",
        "whisper",
        "faiss",
        "scipy",
        "numba",
        "llvmlite",
        "sklearn",
        "tokenizers",
        "safetensors",
        "huggingface_hub",
        "ctranslate2",
        "av",
        "onnxruntime",
        "tkinter",
        "matplotlib.tests",
        "numpy.tests",
        "pandas.tests",
        "pytest",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)
pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AdvancedVideoQAPro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "desktop_app" / "resources" / "icons" / "app.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AdvancedVideoQAPro",
)
