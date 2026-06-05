# Changelog

## 1.0.0-rc.1

- Completed the local-first desktop product foundation for Advanced Video QA Pro.
- Added PySide6 desktop workspace, project persistence, video library, playback, transcripts, knowledge structuring, embeddings, FAISS, retrieval, evidence, chat, compare, bookmarks, highlights, exports, provider orchestration, diagnostics, and packaging configuration.
- Recovered the UX from stacked developer panels into a tabbed right workspace with first-run guidance.
- Hardened repository publication hygiene by excluding runtime data, model artifacts, build outputs, caches, logs, secrets, and local media.
- Updated public README, screenshot reference, release metadata, and packaging audit coverage.

## Notes

- Release binaries should be published through GitHub Releases, not committed to the repository.
- Provider API keys must be configured locally by each user and must never be committed.
