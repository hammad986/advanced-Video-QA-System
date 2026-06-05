# Retrieval Quality Report

## Query

```text
What is weighted sum?
```

Validation source:

- Project ID: `f85f56b67b77463390f21f102ee40bf7`
- Transcript ID: `00767496-4bb2-4bba-a5c5-8b9e3d7931f4`
- Video: `_699916db92f84bbaad620e06bbb4d481_lc-PyTorch-C1-M1-L2-V4-activation-functions_MP4_1080 (1).mp4`
- Knowledge chunks: `20`

Ground-truth transcript hit:

| Start | End | Text |
|---:|---:|---|
| `69.12s` | `74.64s` | `weighted sum from the input. Let's call their output Z1 and Z2. And your new output neuron takes` |

Ground-truth chunk:

| Chunk ID | Time | Words | Topic |
|---|---:|---:|---|
| `76d370bc-0815-4360-80e0-f475a650aec0` | `63.60s-79.52s` | `47` | `Neural Networks` |

```text
those two neurons are considered a hidden layer. These two neurons independently calculate the weighted sum from the input. Let's call their output Z1 and Z2. And your new output neuron takes both of these inputs and combines them into a single prediction. But here's the problem,
```

## Execution Trace

Existing code path traced:

1. Question enters chat workspace.
2. `RetrievalService.search()` resolves embedding selection through `EmbeddingModelSelector`.
3. `QueryEmbedder.embed()` embeds the question.
4. `FaissSimilaritySearch.search()` runs FAISS search against the project index.
5. `RetrievalService._rank_matches()` deduplicates, applies `min_similarity`, and computes confidence.
6. `EvidenceService.generate()` maps hits into evidence and applies `EvidenceRanker`.
7. `ContextBuilder.build()` filters evidence below `MIN_CONFIDENCE = 0.55` and builds Gemini prompt context.

Relevant code evidence:

- Chunking: `desktop_app/knowledge/chunking_engine.py`
- Retrieval search/ranking: `desktop_app/retrieval/retrieval_service.py`
- Evidence ranking: `desktop_app/evidence/evidence_ranker.py`
- Gemini context building: `desktop_app/answering/context_builder.py`

## Model Comparison

| Selection | Query Embedding Model | Recall@5 | Recall@10 | Relevant Chunk Rank | Context Contains Exact Phrase | Context Contains Formula Support | Direct Definition Present |
|---|---|---:|---:|---:|---|---|---|
| `small` | `BAAI/bge-small-en-v1.5` | `1.00` | `1.00` | `1` | yes | yes | no |
| `base` | `BAAI/bge-base-en-v1.5` | `1.00` | `1.00` | `1` | yes | yes | no |

Answerability measurement:

- Exact phrase criterion: context contains `weighted sum`.
- Formula support criterion: context contains `Wx plus B`, `W times`, `multiplying by weights`, or `adding biases`.
- Direct definition criterion: context contains an explicit definition pattern such as `weighted sum is ...` or `sum of inputs times weights`.

Result:

- Both models retrieve the correct chunk at rank 1.
- Both top-5 contexts contain the exact phrase and formula support.
- Neither top-5 context contains a direct definition sentence.
- The retrieval defect is not a top-k miss for this query.

## Small Model Top-10

Model: `BAAI/bge-small-en-v1.5`

| Rank | Chunk ID | Time | Similarity | Confidence | Contains Ground Truth | Topic |
|---:|---|---:|---:|---:|---|---|
| 1 | `76d370bc-0815-4360-80e0-f475a650aec0` | `63.60s-79.52s` | `0.836498` | `0.711024` | yes | `Neural Networks` |
| 2 | `f53b89dc-281e-4a58-b686-c4f88cdae436` | `337.12s-352.80s` | `0.804423` | `0.683760` | no | `Function Out There Sigmoid` |
| 3 | `5cb39e56-ddd1-484e-a116-272091919160` | `116.32s-134.24s` | `0.775259` | `0.658971` | no | `Neural Networks` |
| 4 | `7235f062-eecd-44fe-8872-254e01d0a3f1` | `274.16s-304.56s` | `0.774302` | `0.658156` | no | `Neural Networks` |
| 5 | `6328cabd-0557-4bb2-80f6-a722727e9fda` | `205.36s-226.08s` | `0.772724` | `0.656815` | no | `Where Wx Plus B` |
| 6 | `543c2b27-ce83-44d5-8e41-bd4648325945` | `79.52s-93.68s` | `0.768684` | `0.653381` | no | `That'S Still Just A` |
| 7 | `d4aca031-0e2f-489d-b2fb-cd9136d944ee` | `134.24s-150.32s` | `0.762674` | `0.648273` | no | `Neural Networks` |
| 8 | `1a6e7145-c65c-49c5-9103-2a2ada3e944c` | `320.80s-337.12s` | `0.761507` | `0.647281` | no | `Neural Networks` |
| 9 | `f37133ac-17d3-4f54-b6c6-ad523ad9a9e9` | `46.72s-63.60s` | `0.753196` | `0.640217` | no | `It Produces Your Final` |
| 10 | `5d44e7b2-af16-45ab-984c-54bfc91e38c1` | `352.80s-369.28s` | `0.747084` | `0.635021` | no | `Neural Networks` |

Small top-5 chunk source text:

1. `63.60s-79.52s`, score `0.836498`

```text
those two neurons are considered a hidden layer. These two neurons independently calculate the weighted sum from the input. Let's call their output Z1 and Z2. And your new output neuron takes both of these inputs and combines them into a single prediction. But here's the problem,
```

2. `337.12s-352.80s`, score `0.804423`

```text
function out there. Sigmoid, for example, will squash your outputs into a range between zero and one, and is great for probabilities. Tanh maps your values to a range between minus one and plus one, which is really useful for many tasks. And there's lots of others too. If you want to dive
```

3. `116.32s-134.24s`, score `0.775259`

```text
its input, something like this. But instead of sending that raw number straight out, we pass it through an activation function like this. And this small change, adding a nonlinear transformation, is what lets your model learn much richer patterns. And now let me introduce you to a really important
```

4. `274.16s-304.56s`, score `0.774302`

```text
But notice we only define two linear layers. In PyTorch, you only code the layers that compute. The input is just your data. And ReLU, well, that's an activation function that transforms values, and not a separate layer in this count. Your first linear layer is your group of neurons. The one means one input feature, and that's the distance. The three means three neurons. So this layer outputs three values. Each of those outputs passes through ReLU. Then the second linear layer takes those
```

5. `205.36s-226.08s`, score `0.772724`

```text
where Wx plus B equals zero, which effectively gives us x equals minus B over W, where it stops outputting zero and starts responding to the input. Now think about your city transportation data. The pattern doesn't just bend once, it curves, shifting gradually across different distances
```

## Base Model Top-10

Model: `BAAI/bge-base-en-v1.5`

| Rank | Chunk ID | Time | Similarity | Confidence | Contains Ground Truth | Topic |
|---:|---|---:|---:|---:|---|---|
| 1 | `76d370bc-0815-4360-80e0-f475a650aec0` | `63.60s-79.52s` | `0.791056` | `0.672398` | yes | `Neural Networks` |
| 2 | `6328cabd-0557-4bb2-80f6-a722727e9fda` | `205.36s-226.08s` | `0.748411` | `0.636149` | no | `Where Wx Plus B` |
| 3 | `f53b89dc-281e-4a58-b686-c4f88cdae436` | `337.12s-352.80s` | `0.745899` | `0.634015` | no | `Function Out There Sigmoid` |
| 4 | `5cb39e56-ddd1-484e-a116-272091919160` | `116.32s-134.24s` | `0.728877` | `0.619545` | no | `Neural Networks` |
| 5 | `f37133ac-17d3-4f54-b6c6-ad523ad9a9e9` | `46.72s-63.60s` | `0.722821` | `0.614398` | no | `It Produces Your Final` |
| 6 | `543c2b27-ce83-44d5-8e41-bd4648325945` | `79.52s-93.68s` | `0.721739` | `0.613478` | no | `That'S Still Just A` |
| 7 | `d4aca031-0e2f-489d-b2fb-cd9136d944ee` | `134.24s-150.32s` | `0.715553` | `0.608220` | no | `Neural Networks` |
| 8 | `7235f062-eecd-44fe-8872-254e01d0a3f1` | `274.16s-304.56s` | `0.714219` | `0.607086` | no | `Neural Networks` |
| 9 | `a82ee549-3e3d-43e5-852d-73fcceb5d396` | `165.20s-188.16s` | `0.713977` | `0.606881` | no | `Introduction` |
| 10 | `42a746a4-293f-43e7-a8c0-481f0fd638a4` | `304.56s-320.80s` | `0.703856` | `0.598277` | no | `Three Transformed Values Combines` |

Base top-5 chunk source text:

1. `63.60s-79.52s`, score `0.791056`

```text
those two neurons are considered a hidden layer. These two neurons independently calculate the weighted sum from the input. Let's call their output Z1 and Z2. And your new output neuron takes both of these inputs and combines them into a single prediction. But here's the problem,
```

2. `205.36s-226.08s`, score `0.748411`

```text
where Wx plus B equals zero, which effectively gives us x equals minus B over W, where it stops outputting zero and starts responding to the input. Now think about your city transportation data. The pattern doesn't just bend once, it curves, shifting gradually across different distances
```

3. `337.12s-352.80s`, score `0.745899`

```text
function out there. Sigmoid, for example, will squash your outputs into a range between zero and one, and is great for probabilities. Tanh maps your values to a range between minus one and plus one, which is really useful for many tasks. And there's lots of others too. If you want to dive
```

4. `116.32s-134.24s`, score `0.728877`

```text
its input, something like this. But instead of sending that raw number straight out, we pass it through an activation function like this. And this small change, adding a nonlinear transformation, is what lets your model learn much richer patterns. And now let me introduce you to a really important
```

5. `46.72s-63.60s`, score `0.722821`

```text
it produces your final prediction, so it is the output layer. But when you add a second neuron, now you have two outputs from your single input, and you need a single prediction in your final output. So you add another neuron to combine these two outputs into one final output. And now
```

## Final Gemini Context

This is the app-default top-5 context for `BAAI/bge-small-en-v1.5`.

```text
Use ONLY the evidence below. If the evidence does not directly support the answer, return exactly: I could not find enough evidence in the loaded videos.
Every factual sentence must include at least one citation marker like [1].

Question: What is weighted sum?

Evidence:
[1] Source Video: _699916db92f84bbaad620e06bbb4d481_lc-PyTorch-C1-M1-L2-V4-activation-functions_MP4_1080 (1).mp4
Chunk ID: 76d370bc-0815-4360-80e0-f475a650aec0
Timestamp: 63.6s - 79.5s
Confidence: 0.711
Evidence Text: those two neurons are considered a hidden layer. These two neurons independently calculate the weighted sum from the input. Let's call their output Z1 and Z2. And your new output neuron takes both of these inputs and combines them into a single prediction. But here's the problem,

[2] Source Video: _699916db92f84bbaad620e06bbb4d481_lc-PyTorch-C1-M1-L2-V4-activation-functions_MP4_1080 (1).mp4
Chunk ID: f53b89dc-281e-4a58-b686-c4f88cdae436
Timestamp: 337.1s - 352.8s
Confidence: 0.684
Evidence Text: function out there. Sigmoid, for example, will squash your outputs into a range between zero and one, and is great for probabilities. Tanh maps your values to a range between minus one and plus one, which is really useful for many tasks. And there's lots of others too. If you want to dive

[3] Source Video: _699916db92f84bbaad620e06bbb4d481_lc-PyTorch-C1-M1-L2-V4-activation-functions_MP4_1080 (1).mp4
Chunk ID: 5cb39e56-ddd1-484e-a116-272091919160
Timestamp: 116.3s - 134.2s
Confidence: 0.659
Evidence Text: its input, something like this. But instead of sending that raw number straight out, we pass it through an activation function like this. And this small change, adding a nonlinear transformation, is what lets your model learn much richer patterns. And now let me introduce you to a really important

[4] Source Video: _699916db92f84bbaad620e06bbb4d481_lc-PyTorch-C1-M1-L2-V4-activation-functions_MP4_1080 (1).mp4
Chunk ID: 7235f062-eecd-44fe-8872-254e01d0a3f1
Timestamp: 274.2s - 304.6s
Confidence: 0.658
Evidence Text: But notice we only define two linear layers. In PyTorch, you only code the layers that compute. The input is just your data. And ReLU, well, that's an activation function that transforms values, and not a separate layer in this count. Your first linear layer is your group of neurons. The one means one input feature, and that's the distance. The three means three neurons. So this layer outputs three values. Each of those outputs passes through ReLU. Then the second linear layer takes those

[5] Source Video: _699916db92f84bbaad620e06bbb4d481_lc-PyTorch-C1-M1-L2-V4-activation-functions_MP4_1080 (1).mp4
Chunk ID: 6328cabd-0557-4bb2-80f6-a722727e9fda
Timestamp: 205.4s - 226.1s
Confidence: 0.657
Evidence Text: where Wx plus B equals zero, which effectively gives us x equals minus B over W, where it stops outputting zero and starts responding to the input. Now think about your city transportation data. The pattern doesn't just bend once, it curves, shifting gradually across different distances
```

## Factor Verification

### Chunking Strategy Too Large

Finding: no evidence for this query.

Evidence:

- Ground-truth chunk is `47` words.
- Chunking config is `min_chunk_words=45`, `max_chunk_words=260`.
- The answer phrase is isolated in a small chunk, not buried in an oversized chunk.

### Chunk Overlap Insufficient

Finding: supported.

Evidence:

- The ground-truth chunk starts mid-reference: `those two neurons...`
- The ground-truth chunk ends mid-transition: `But here's the problem,`
- The preceding adjacent chunk at `46.72s-63.60s` explains why an additional neuron combines outputs.
- The following adjacent chunk at `79.52s-93.68s` explains `multiplying by weights and adding biases`.
- Current chunking has no overlap; adjacent context is only included if FAISS retrieves it separately.

### Ranking Poor

Finding: not for this exact query.

Evidence:

- `small` ranks the ground-truth chunk `#1`.
- `base` ranks the ground-truth chunk `#1`.
- Recall@5 and Recall@10 are both `1.00`.

Secondary finding:

- `topic_score` is `0.000` for all top-10 results because generated topic titles do not contain query terms.
- Ranking is effectively semantic similarity only for this query.

### Evidence Threshold Too Strict

Finding: no evidence for this query.

Evidence:

- ContextBuilder threshold is `0.55`.
- Ground-truth chunk confidence is `0.711` for small and `0.672` for base.
- Both pass the threshold.

### Transcript Segmentation Loses Context

Finding: supported.

Evidence:

- Exact transcript segment containing the answer is only a fragment:

```text
weighted sum from the input. Let's call their output Z1 and Z2. And your new output neuron takes
```

- The chunk text also begins with a pronoun/reference:

```text
those two neurons are considered a hidden layer.
```

- The retrieved evidence identifies the relevant concept but does not provide a clean direct definition.

### Embedding Model Quality Insufficient

Finding: not for this exact query.

Evidence:

- `BAAI/bge-small-en-v1.5`: ground-truth rank `1`, similarity `0.836498`.
- `BAAI/bge-base-en-v1.5`: ground-truth rank `1`, similarity `0.791056`.
- Base did not improve rank or recall.
- Small produced the higher similarity and confidence for the ground-truth chunk.

## Measurable Findings

1. Relevant evidence is retrieved.

Measured result:

- `small`: rank `1`, Recall@5 `1.00`, Recall@10 `1.00`.
- `base`: rank `1`, Recall@5 `1.00`, Recall@10 `1.00`.

2. The likely failure is answerability, not retrieval recall.

Measured result:

- Top-5 context contains the exact phrase `weighted sum`.
- Top-5 context contains related formula support: `Wx plus B`.
- Top-5 context does not contain a direct definition sentence.
- Previous Gemini output returned the insufficiency response despite retrieved citations.

3. The most evidence-backed retrieval-quality issue is missing adjacent context.

Measured result:

- The ground-truth chunk is a fragment at `63.60s-79.52s`.
- Adjacent chunks at `46.72s-63.60s` and `79.52s-93.68s` contain needed setup/explanation.
- Current chunking stores no overlap.

## Evidence-Backed Recommendations

No code changes were made for this audit.

Recommended fixes, based only on measured evidence:

1. Add chunk overlap during knowledge generation.

Evidence: the answer chunk starts and ends as a fragment, while adjacent chunks contain necessary setup and explanation.

2. Evaluate adjacent chunk inclusion for answer context.

Evidence: the relevant chunk is rank 1, but answerability depends on neighboring context.

3. Do not switch from `BAAI/bge-small-en-v1.5` to `BAAI/bge-base-en-v1.5` as a fix for this query.

Evidence: base did not improve rank, Recall@5, Recall@10, or direct answerability.

4. Do not lower the evidence threshold for this query.

Evidence: all top-5 chunks already pass `0.55`; the ground-truth chunk passes with margin.

5. Do not treat this as a FAISS retrieval miss.

Evidence: the ground-truth chunk is rank 1 for both embedding models.

Raw audit artifact:

- `tmp/sprint37_retrieval_quality.json`
