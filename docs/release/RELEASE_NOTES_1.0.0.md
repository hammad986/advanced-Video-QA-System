# Advanced Video QA Pro 1.0.0 Release Notes

Advanced Video QA Pro is a local-first Windows desktop workbench for researching video content with transcripts, retrieval, evidence, grounded chat, and multi-video comparison.

## Highlights

- Windows desktop application shell with persistent projects, layout, settings, diagnostics, and crash recovery.
- Local video library, playback, transcript generation, transcript viewer, and knowledge chunking.
- Local BGE embeddings, FAISS vector indexing, retrieval, evidence panel, and citation-aware chat.
- Multi-video compare workspace for agreements, differences, unique concepts, missing topics, contradictions, and timeline differences.
- Bookmarks, highlights, research exports, provider dashboard, diagnostics center, and encrypted provider credential storage.
- BYOK provider support with real health checks and safe generation validation.

## Validated Providers

- Gemini: health check passed and safe generation returned exactly `OK`.
- OpenAI: authentication/model health passed, but safe generation hit HTTP `429` during RC validation.
- Anthropic, Groq, OpenRouter, Ollama, LM Studio: supported by configuration, not configured in the RC validation environment.

## Known Limitations

- OpenAI generation requires available quota/rate limit capacity.
- Update checks require `ADVANCED_VIDEO_QA_RELEASES_API_URL` to point to a GitHub Releases API endpoint.
- The current Gemini implementation uses `google.generativeai`; migration to `google.genai` is planned without answer-pipeline redesign.
- EXE packaging includes large ML dependencies and should be validated on a clean Windows VM before public distribution.

## Validation Summary

- Test suite: `134 passed, 1 skipped`.
- Real-video RC workflow: import, transcript, knowledge, embeddings, FAISS, retrieval, evidence, chat, compare, and exports completed.
- Export formats validated: JSON, Markdown, PDF.
