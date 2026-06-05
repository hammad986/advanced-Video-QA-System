# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path


block_cipher = None
ROOT = Path(SPECPATH).parent

datas = [
    (str(ROOT / "desktop_app" / "resources"), "desktop_app/resources"),
    (str(ROOT / ".env.example"), "."),
]

excluded_ai_packages = [
    "torch",
    "torchaudio",
    "torchvision",
    "transformers",
    "sentence_transformers",
    "faster_whisper",
    "whisper",
    "faiss",
    "numba",
    "llvmlite",
    "scipy",
    "sklearn",
    "gevent",
    "IPython",
    "notebook",
    "jupyter",
    "matplotlib",
    "matplotlib_inline",
    "google.generativeai",
    "googleapiclient",
    "google.ai",
    "google.api_core",
    "grpc",
    "openai",
    "anthropic",
    "groq",
    "pandas",
    "pyarrow",
    "botocore",
    "boto3",
    "sqlalchemy",
    "psycopg2",
    "pytest",
    "_pytest",
    "ipykernel",
    "ipywidgets",
    "jupyter_client",
    "zmq",
    "lxml",
    "PIL",
    "tkinter",
    "_tkinter",
    "tornado",
]

a = Analysis(
    [str(ROOT / "desktop_app" / "shell_main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excluded_ai_packages,
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
