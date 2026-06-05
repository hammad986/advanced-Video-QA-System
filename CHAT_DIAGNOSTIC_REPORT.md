# Chat Diagnostic Report

## Root Cause

The Ask/Send workflow was failing before provider execution because the active project had no FAISS index for the selected embedding model.

Live database evidence from `C:\Users\mdham\AppData\Local\AdvancedVideoQA\app.db` before validation:

- `knowledge_chunks`: `0`
- `embeddings`: `0`
- `vector_indexes`: `0`
- configured provider: `gemini`
- configured model: `gemini-2.5-flash`
- embedding selection: `small`
- resolved embedding model: `BAAI/bge-small-en-v1.5`

Exact exception captured through the real chat service path:

```text
desktop_app.retrieval.retrieval_service.RetrievalError:
No FAISS index found for BAAI/bge-small-en-v1.5. Build the vector index first.
```

Failing file and line:

- `desktop_app/retrieval/retrieval_service.py:48`

Stack trace:

```text
File "desktop_app\chat\chat_service.py", line 34, in ask
  result = self.answer_service.answer(...)
File "desktop_app\answering\answer_service.py", line 291, in answer
  evidence_result = self.evidence_service.generate(...)
File "desktop_app\evidence\evidence_service.py", line 37, in generate
  retrieval_result = self.retrieval_service.search(...)
File "desktop_app\retrieval\retrieval_service.py", line 48, in search
  raise RetrievalError(f"No FAISS index found for {embedding_model}. Build the vector index first.")
```

## Execution Path

- UI Ask/Send button: `desktop_app/widgets/chat_workspace.py:67`
- Chat workspace signal: `desktop_app/widgets/chat_workspace.py:113-118`
- Main window dispatch: `desktop_app/main_window.py:1520-1539`
- Chat manager async job: `desktop_app/chat/chat_manager.py:26-53`
- Chat service: `desktop_app/chat/chat_service.py:24-45`
- Answer service: `desktop_app/answering/answer_service.py:301-412`
- Evidence service: `desktop_app/evidence/evidence_service.py:28-45`
- Retrieval service: `desktop_app/retrieval/retrieval_service.py:39-48`
- Provider execution: `desktop_app/answering/answer_service.py:346-352`
- Response rendering: `desktop_app/main_window.py:1541-1560`

Provider Router evidence:

- `desktop_app/providers/provider_router.py` exists.
- The current chat path does not call `ProviderRouter`.
- Current provider selection is handled by `ProviderExecutor._selected_profile()` in `desktop_app/answering/answer_service.py:69-74`.

## Fix Applied

Actionable error propagation:

- Added `ChatPipelineError`: `desktop_app/answering/answer_service.py:33`
- Added actionable error mapping: `desktop_app/answering/answer_service.py:433-456`
- Main window now displays `state.error_message`: `desktop_app/main_window.py:1562-1567`
- Grounded answer failures also display `state.error_message`: `desktop_app/main_window.py:1608-1615`

Structured logging:

- Log file: `logs/chat_pipeline.log`
- Writer: `desktop_app/answering/answer_service.py:459-467`
- Logs include provider, model, query, retrieval count, evidence count, provider latency, exception message, and traceback.

Chat UX correction:

- Conversation area before input: `desktop_app/widgets/chat_workspace.py:61-65`
- Send button text: `desktop_app/widgets/chat_workspace.py:53`
- Enter sends, Shift+Enter inserts newline: `desktop_app/widgets/chat_workspace.py:21-31`
- Auto-focus input: `desktop_app/widgets/chat_workspace.py:70`
- Disable Send while processing: `desktop_app/widgets/chat_workspace.py:94-103`
- Loading indicator: `desktop_app/widgets/chat_workspace.py:102-103`
- Error text displayed in chat panel: `desktop_app/widgets/chat_workspace.py:107-111`

Retrieval count logging support:

- `desktop_app/evidence/evidence_service.py:26`
- `desktop_app/evidence/evidence_service.py:45`

## Before / After Screenshots

Before layout reconstruction from pre-fix source:

![Before chat layout](tmp/sprint36_5_before_chat_layout.png)

After corrected chat layout with real chat message:

![After chat layout](tmp/sprint36_5_after_chat_layout.png)

## Validation Evidence

Focused compile:

```text
py -m compileall desktop_app\answering\answer_service.py desktop_app\evidence\evidence_service.py desktop_app\widgets\chat_workspace.py desktop_app\main_window.py
Result: passed
```

Focused tests:

```text
py -m pytest tests\test_answering_foundation.py tests\test_chat_workspace.py tests\test_main_window_smoke.py -q
Result: 18 passed in 12.00s
```

Full compile:

```text
py -m compileall desktop_app tests
Result: passed
```

Full tests:

```text
py -m pytest -q
Result: 145 passed, 1 skipped in 61.60s
```

Live failure after fix:

```text
EXCEPTION_TYPE= ChatPipelineError
EXCEPTION_MESSAGE= No FAISS index available. Build embeddings and the FAISS index before asking. Details: No FAISS index found for BAAI/bge-small-en-v1.5. Build the vector index first.
```

`logs/chat_pipeline.log` failure record includes:

```json
{
  "event": "chat_failed",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "query": "What is weighted sum?",
  "retrieval_count": 0,
  "evidence_count": 0,
  "exception_type": "RetrievalError",
  "actionable_error": "No FAISS index available. Build embeddings and the FAISS index before asking. Details: No FAISS index found for BAAI/bge-small-en-v1.5. Build the vector index first."
}
```

Real video validation input:

- Video: `_699916db92f84bbaad620e06bbb4d481_lc-PyTorch-C1-M1-L2-V4-activation-functions_MP4_1080 (1).mp4`
- Completed transcript: `00767496-4bb2-4bba-a5c5-8b9e3d7931f4`
- Transcript segments: `68`
- Transcript contains weighted sum text at `69.12s-74.64s`.

Generated validation artifacts:

- Knowledge chunks: `20`
- Embeddings: `20`
- Embedding dimension: `384`
- FAISS vectors: `20`
- FAISS index: `C:\Users\mdham\AppData\Local\AdvancedVideoQA\projects\VectorIndexes\BAAI__bge-small-en-v1.5.faiss`

Question asked:

```text
What is weighted sum?
```

Chat result:

- Provider: `gemini`
- Model: `gemini-2.5-flash`
- Provider latency: `32914.422 ms`
- Total duration: `33058.640 ms`
- Retrieval count: `5`
- Evidence count: `5`
- Citation count: `5`
- Chat messages saved: `1`
- Retrieval history rows: `1`
- Evidence history rows: `5`

Latest successful log record:

```json
{
  "event": "chat_completed",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "query": "What is weighted sum?",
  "retrieval_count": 5,
  "evidence_count": 5,
  "provider_latency_ms": 32914.42210000241,
  "duration_ms": 33058.63989997306
}
```

Provider response caveat:

```text
I could not find enough evidence in the loaded videos.
```

The response was produced by the provider and saved with citations. Retrieval, evidence, provider execution, response persistence, and citation rendering all completed. The content was an insufficiency answer, not a factual weighted-sum explanation.
