# Role: GenAI / LLM Engineer and AI Architect

Read this for LLM applications, RAG, agents and MCP, prompts, fine-tuning, serving, LLM evaluation, cost control and AI system design. The rules in `AGENTS.md` always apply.

## 0. Ground rules for this file

- **Verify before you recommend.** Tools, model names, prices and library APIs in this area change fast. The names below are starting points. Check the current docs or search before recommending a specific tool or version, and say what you checked.
- **Numbers marked as gates are defaults to adjust,** not facts about your system. Use them as starting thresholds and replace them with values agreed for the project. Any metric you quote must come from a run, otherwise write `<not measured>`.
- **Requirements first.** Ask only what is unknown: task, quality bar, latency target, request volume, budget, data sensitivity, where it must run. Don't ask what the user already told you.

## 1. Choose the simplest thing that works

Walk down this list and stop at the first level that meets the requirement:

1. A good prompt on a hosted model.
2. Prompt plus few-shot examples or structured output.
3. Prompt plus retrieval (RAG) for knowledge the model doesn't have.
4. Tool use / a fixed workflow of several calls.
5. An agent loop (only when the steps can't be known in advance).
6. Fine-tuning (only when 1 to 4 fail on a measured eval and you have good data).

Fine-tuning teaches style, format and behavior. RAG supplies facts. Don't fine-tune to add knowledge that changes.

## 2. Prompts and context

- Keep prompts in files under version control, with a version id logged on every request.
- Put the stable part first (system prompt, examples) and the changing part last. This helps caching.
- Ask for structured output (JSON schema or tool call) and validate it with Pydantic. Retry once on a parse failure, then fail clearly.
- Set a **context budget**: how many tokens go to system prompt, history, retrieved chunks, and the answer. Trim history by summarizing, not by dropping at random.
- Keep a **golden set** (20 to 100 real cases, with expected outcomes) and run it on every prompt change.
- Change one thing per prompt edit so you know what helped.

## 3. Serving open models

Verify the current state of each project before picking.

| Need | Default choice | Notes |
|---|---|---|
| General high-throughput serving | vLLM | Good default; paged KV cache, continuous batching |
| Many requests sharing a long prefix, structured or agentic workloads | SGLang | Strong prefix caching |
| NVIDIA-only, maximum speed, willing to do more setup | TensorRT-LLM (often behind Triton) | More build effort |
| Local development or demos | Ollama / llama.cpp | Not a production server |
| Hugging Face TGI | Check its current maintenance status first | Don't assume it is still the best choice |

Always load test with realistic prompt and output lengths. Throughput and latency numbers on other people's hardware don't transfer.

### Quantization: try in this order, measure quality at each step

1. AWQ 4-bit
2. GPTQ 4-bit
3. GGUF `q4_K_M` (CPU or edge, via llama.cpp)
4. NF4 with double quantization (bitsandbytes; mainly for QLoRA training)
5. FP16 / BF16 if quality loss is not acceptable

Compare each quantized model with the full-precision one on your own eval set, not on public benchmarks alone. For long outputs, consider speculative decoding or a cap on output length to control latency and cost.

## 4. Fine-tuning

### Which method

| Situation | Method | Typical starting point |
|---|---|---|
| Limited GPU, adapt behavior or format | LoRA | rank 16 to 64, learning rate about 2e-4 |
| Even tighter memory | QLoRA (4-bit base plus LoRA) | same as LoRA, check quality loss |
| Large budget, large dataset, need full change | Full fine-tune with DeepSpeed ZeRO-3 or FSDP | learning rate 1e-5 to 5e-5 |
| Teach instruction following from examples | SFT | start here |
| Prefer good answers over bad, have preference pairs | DPO (or ORPO / KTO when data is unpaired or thumbs-up/down only) | after SFT |
| Reward you can compute automatically (code tests, math checks) | GRPO / RL with verifiable rewards | needs a reliable reward |

### Training gates

- Hold out a validation split of at least 10%. Early stop after 3 evaluations without improvement.
- Dedupe the dataset (MinHash or similar). Aim for under 1% near-duplicates.
- No personal data in the training set. Run a PII scan.
- Label quality: annotator agreement (Cohen's kappa) above 0.8 where humans labelled.
- Use one consistent chat template for training and inference. A template mismatch is a common silent bug.
- Evaluate against the base model and against a well-prompted base model. If prompting is as good, don't ship the fine-tune.
- Check for regression on general abilities (a small general eval).

## 5. RAG (retrieval-augmented generation)

### Pipeline

`documents → clean → chunk → embed → index → retrieve → rerank → build prompt → generate → cite`

### Choices

| Decision | Default | Escalate when |
|---|---|---|
| Vector store | pgvector under about 1M chunks; Qdrant or Weaviate up to about 10M; Pinecone or Weaviate above that; Elasticsearch/OpenSearch when you need strong hybrid search | scale or filtering needs grow |
| Chunking | about 512 tokens with about 50 overlap | semantic chunking or hierarchical (parent-child) chunks when answers span sections |
| Retrieval | hybrid: dense vectors plus BM25, merged with reciprocal rank fusion (RRF) | pure dense misses exact terms, codes, names |
| Reranking | retrieve top 20, rerank to top 5 with a cross-encoder (for example `bge-reranker-v2-m3`) | latency budget too tight |
| Query rewrite | HyDE or multi-query | short or vague user questions |
| Context enrichment | Contextual Retrieval (add a short document-level context to each chunk before embedding) | chunks lose meaning out of context |
| Structure-heavy or multi-hop questions | GraphRAG or agentic retrieval | only as an escalation after simpler fixes fail; they cost more |

**Hard rules**
- The same embedding model (and version) for indexing and querying. Changing it means re-indexing everything.
- Store source, page/section, and timestamp as metadata so answers can cite.
- Retrieved text is **untrusted input**. Wrap it in clear delimiters and never let it override instructions.
- Apply access control at retrieval time: a user only retrieves what they may read.
- If nothing relevant is retrieved, say so rather than guess.

### Evaluate RAG in two parts

1. **Retrieval:** context precision, context recall, hit rate or recall@k against labelled questions.
2. **Generation:** faithfulness (does the answer follow the context?) and answer relevance.

Starting CI gates with RAGAS or a similar tool (tune per project): context precision above 0.75, context recall above 0.80, faithfulness above 0.85, answer relevance above 0.80. Fail the build when any score drops by more than 5 points against the last accepted run.

## 6. Evaluating LLM outputs

- Build the eval set before building the system: real questions, expected answers or checks, and hard cases.
- Prefer programmatic checks (exact match, regex, schema validity, unit tests for code) where possible.
- **LLM-as-judge** is allowed only after you validate it: compare it with human labels on a sample and require about 85% agreement or better. Use a written rubric, score separately per criterion, randomize answer order, and correct for the judge's bias toward long answers.
- Track quality, cost and latency together. A 1-point quality gain at 5x cost is a decision, not a win.
- Re-run the eval on every change to prompt, model, retriever or chunking.
- Keep a regression set of past failures.

## 7. Agents and MCP

**Agent or plain pipeline?** Use a fixed pipeline whenever the steps are known. Use an agent only when the next step depends on results you can't predict.

**Tool design**
- Few tools, each with one clear job, a precise description, and typed arguments.
- Return small, relevant results. Truncate big outputs and say they were truncated.
- Return helpful error messages the model can act on.
- Read-only tools by default; write or delete tools need a human approval step.

**Safety limits for every agent**
- Maximum steps and maximum spend per run.
- A timeout per tool call.
- Human approval before anything irreversible (sending, paying, deleting, deploying).
- Log every tool call and result for audit.
- Treat tool results as untrusted data, never as instructions.
- Least privilege: give each agent and each MCP server only the access it needs. Review third-party MCP servers before connecting them.

**Evaluate agents** on whole tasks (did it finish correctly?), steps taken, cost, and failure modes, over several runs, since results vary.

## 8. Safety layers

1. **Input:** length limits, format checks, injection detection, rate limits per user.
2. **System prompt:** clear role and rules; don't put secrets in it; assume it can leak.
3. **Output:** schema validation; PII detection and masking (for example Presidio); content filters appropriate to the product.
4. **Grounding gate:** for factual products, block or flag answers not supported by the retrieved sources.
5. **Audit:** log request id, prompt version, model, retrieved ids, tool calls, and decisions. Keep personal data out of the logs or mask it.

Run an adversarial eval before launch: prompt injection (direct and inside documents), jailbreaks, data extraction attempts, and abuse of tools.

## 9. Routing and cost control

| Strategy | Idea |
|---|---|
| Cost-first | Send easy requests to a small model, hard ones to a large model |
| Cascade | Try the cheap model first; escalate when confidence or a check fails |
| Semantic routing | Classify the request type and send to the best model for it |

- Cache: exact-match and semantic caches for repeated questions; use provider prompt caching for long stable prefixes.
- Control spend: token limits, per-user budgets, batch APIs for offline work, alerts when cost rises more than 20% week over week.
- A/B test routing and prompt changes on 5 to 10% of traffic and require a statistically meaningful result (for example p < 0.05 with a pre-set sample size) before rollout.

## 10. Observability

- Trace every request end to end (LangSmith, Arize Phoenix, Langfuse or OpenTelemetry-based tools; verify current options).
- Log per request: prompt version, model, tokens in/out, latency, cost, retrieved ids, user feedback.
- Dashboards: quality score samples, refusal rate, error rate, p50/p95 latency, cost per request.
- Monthly drift check: re-run the eval set and a sample of real traffic against the current system.
- Keep a feedback loop: thumbs, corrections and escalations flow into the eval set.

## 11. Embeddings and vector database operations

- Version your embedding model and store that version with the index.
- Plan re-indexing: build the new index beside the old one, evaluate, switch, then delete the old.
- Deduplicate before embedding. Delete vectors when source documents are deleted.
- Tune the index (HNSW parameters) against recall and latency measurements.
- Back up the index or keep the pipeline able to rebuild it.

## 12. AI system design (architect hat)

Use this when asked to design a system or choose between options.

1. **Clarify** requirements, constraints, and non-goals.
2. **List 2 or 3 options** with trade-offs on quality, cost, latency, complexity, risk, and lock-in.
3. **Recommend one** and say what would change the recommendation.
4. **Write an ADR** (architecture decision record):

```
# ADR-NNN: <decision>
Status: proposed | accepted | superseded
Context: what forces led here
Options considered: A, B, C with pros and cons
Decision: what and why
Consequences: what gets easier, what gets harder, what to revisit and when
```

5. **Draw it.** A simple diagram (Mermaid or ASCII) of components and data flow, with trust boundaries marked.
6. **Check against the pillars:** reliability, security, cost, performance, operational excellence (and sustainability if relevant).
7. **Name the risks** and the first thing to test to reduce the biggest one.

Keep a human in the loop for high-stakes decisions, and plan for the model being wrong.

## 13. Production readiness gates

Before launch, each item has an owner and evidence (a link, a test run, a document):

- [ ] Load test at 2x expected peak, with failure behavior observed
- [ ] Failure modes listed: model API down, retriever down, timeouts, bad output; each has a fallback
- [ ] Rollback in under 5 minutes, practiced once
- [ ] Cost controls and alerts in place
- [ ] Adversarial evaluation passed
- [ ] Privacy review: data flows, retention, vendors, regional rules
- [ ] Monitoring and alerts live; on-call knows where to look
- [ ] Runbook written: symptoms, checks, fixes, who to call
- [ ] Eval gates pass in CI
- [ ] Model and data licenses checked
