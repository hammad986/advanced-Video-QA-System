# Changelog Review

## 1.0.0

### Added

- PySide6 Windows desktop application with project workspace, split-panel layout, settings, provider hub, and diagnostics.
- Research project persistence backed by SQLite migrations.
- Video import, metadata extraction, thumbnails, playback, timeline controls, snapshots, and transcript generation.
- Transcript viewer with search, timestamp navigation, video sync, and TXT/Markdown/JSON export.
- Knowledge structuring, local BGE embeddings, FAISS vector indexes, retrieval history, and evidence ranking.
- Grounded chat, persistent chat sessions, citations, provider visibility, and usage/cost tracking.
- Multi-video compare workspace with evidence-linked results.
- Bookmarks, highlights, research report exports, diagnostics panel, provider dashboard, and crash recovery.
- Memory optimization, model isolation, worker pooling, adaptive runtime profiles, and low-memory support.
- Provider orchestration, real provider health checks, encrypted credential storage, and safe generation validation.
- First-run wizard, update check foundation, PyInstaller spec, Inno Setup installer configuration, and release icon.

### Security

- Provider API keys are migrated from legacy `.env` values into Windows Credential Manager / DPAPI-backed storage.
- `.env.example` has been sanitized and contains placeholders only.

### Known Issues

- OpenAI generation validation may fail with HTTP `429` when quota/rate limits are unavailable.
- Gemini SDK migration from `google.generativeai` to `google.genai` remains pending.
- Public update notifications require a configured GitHub Releases API URL.
