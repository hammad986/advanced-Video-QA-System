# Gemini SDK Migration Audit

## Current State

The answer provider execution path currently imports:

```python
import google.generativeai as genai
```

This is used only for Gemini answer generation. It is not part of chunking, embeddings, FAISS indexing, retrieval, evidence ranking, or compare logic.

## Release Finding

During Sprint 25 provider generation validation, Gemini returned exactly `OK`, but Python emitted a deprecation warning indicating that `google.generativeai` support has ended and migration to `google.genai` is recommended.

## Migration Scope

No answer-pipeline redesign is required. The migration should be isolated to the Gemini provider adapter.

### Replace

- `genai.configure(api_key=...)`
- `genai.GenerativeModel(model_name)`
- `model.generate_content(prompt)`
- `response.text`
- `response.usage_metadata`

### With

- `google.genai.Client(api_key=...)`
- `client.models.generate_content(model=..., contents=...)`
- new SDK response text and usage fields.

## Risks

- Response object shape differs from the deprecated SDK.
- Token usage metadata mapping must be revalidated.
- Existing tests should mock Gemini adapter behavior rather than the whole answer service.

## Recommendation

Ship V1.0 only if the warning is accepted as a known limitation. Otherwise complete the SDK migration as a patch release blocker before public announcement.
