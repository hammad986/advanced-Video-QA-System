# Admin Guide — Advanced Video QA Pro

This guide covers repository and release administration for the local-first desktop application.

## Release Artifacts

- Source repository: application source, documentation, tests, and packaging configuration.
- GitHub Releases: Windows installer, release notes, checksums, and optional packaged ZIPs.
- Do not commit `dist/`, `build/`, `tmp/`, `data/`, `models/`, virtual environments, logs, databases, secrets, or user media.

## Packaging

Build the desktop distribution with:

```powershell
python -m PyInstaller packaging/AdvancedVideoQAPro.spec --noconfirm --clean
```

Build the Windows installer with Inno Setup:

```powershell
ISCC.exe packaging/AdvancedVideoQAPro.iss
```

## Validation Checklist

- Source tests pass.
- `AdvancedVideoQAPro.exe` launches.
- FFmpeg and FFprobe are present in the packaged runtime.
- Whisper/faster-whisper, Torch, SentenceTransformers, and FAISS are present in the packaged runtime.
- README screenshot references resolve.
- `.env` and runtime credentials are absent from the source repository.
- Release binaries are uploaded as release assets, not committed.

## Security

Provider API keys belong in encrypted local credential storage on the user machine. Never commit provider secrets, local databases, transcripts, user media, generated embeddings, model files, or release logs.

Powered by Aetherion Labs
