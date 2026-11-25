# Role: Backend, Testing, MLOps and Delivery

Read this for APIs and services around models, automated tests (unit to load), CI/CD, Docker, cloud, releases and handoff documentation. Rules in `AGENTS.md` always apply.

---

## Part A. Backend for model serving (Python)

### Structure
- FastAPI by default for new ML/LLM services (follow the project's existing framework, such as Django, if it has one).
- Separate layers: routes (HTTP only), services (logic), clients (model, DB, vector store), schemas (Pydantic).
- Load the model once at startup (lifespan handler), not per request.
- Config from environment variables with a typed settings class. No secrets in code.

### API habits
- Validate every input with Pydantic; set size limits on text and files.
- Return consistent error shapes and correct status codes (400/401/403/404/422/429/500/503).
- Add `/health` (process is up) and `/ready` (model loaded, dependencies reachable).
- Timeouts on every outbound call. Retries with backoff only for safe (idempotent) operations.
- Rate limit per user or key. Add request ids to logs.
- Version the API (`/v1/...`) and don't break existing clients.

### Streaming (LLM output)
- Use Server-Sent Events or streaming responses; send tokens as they arrive.
- Handle client disconnects by cancelling the upstream generation.
- Send a final event with usage and finish reason; send an explicit error event if generation fails midway.

### Auth and security
- Authenticate every non-public route (API keys, OAuth/JWT per the project). Authorize per resource.
- Never log request bodies that may hold personal data or secrets.
- CORS allow-list, not `*`, for authenticated APIs.
- Keep dependencies updated and scanned.
- Slow work (batch inference, big documents) goes to a queue (Celery, RQ, Cloud Tasks) with a job status endpoint.

---

## Part B. Testing (QA, SDET and ML/LLM evals combined)

### One pyramid
Aim for roughly: **80% unit, 15% integration, 5% end-to-end.** Fast tests first.

| Level | Tools | Covers |
|---|---|---|
| Unit | `pytest`, `pytest-cov`, `hypothesis` for property tests | pure logic, transforms, parsers |
| API / integration | `httpx` + FastAPI `TestClient`, `factory_boy`, `testcontainers` (real Postgres, Redis, vector DB) | routes, DB, queues |
| End-to-end / UI | Playwright for Python | key user flows only |
| Load | Locust (or k6) | latency and throughput under load, including streaming |

### Rules
- Test behavior, not implementation. A test must fail when the behavior breaks.
- Each test is independent and deterministic. Fix seeds, freeze time, avoid network calls to real third parties (use recorded or fake responses).
- Name tests by what they prove: `test_rejects_empty_prompt`.
- Cover the edges: empty, huge, wrong type, unicode, concurrent, timeout, dependency down.
- Bug found? Write the failing test first, then fix.
- **No coverage gaming.** Coverage shows what is untested; it doesn't prove quality. Don't add empty tests to move a number. Never delete or skip a failing test to get green.
- Mocks are for slow or external things. If everything is mocked, you are testing the mocks; keep some tests on real components (testcontainers).

### ML and LLM specific tests
- **Data tests:** schema, ranges, no train/test overlap.
- **Model tests:** output shape and type, determinism with a fixed seed, invariance (small harmless changes shouldn't flip the answer), minimum performance on a fixed small eval set.
- **LLM tests:** golden set with checks that don't depend on exact wording (schema valid, contains required facts, refuses what it must refuse). Use a judge only if validated (see `roles/genai.md`).
- **Regression set:** every past production failure becomes a test case.
- **Prompt-injection tests:** documents and tool outputs containing hostile instructions must not change behavior.
- Keep a cheap fast eval for every commit and a bigger one nightly or before release. Track cost of eval runs.

### Flaky tests
Find the cause (time, ordering, shared state, network). Quarantine with a ticket and a deadline; never just retry forever.

---

## Part C. MLOps, CI/CD and deployment

### Docker
- Small base image, pinned versions, multi-stage build, non-root user.
- Don't bake secrets or large model weights carelessly; mount or download weights at start from a trusted store, pinned by hash.
- `.dockerignore` to keep the context small.
- GPU images: match CUDA, driver and framework versions; test on the target hardware.

### CI pipeline (GitHub Actions or the project's CI)
Order: lint and format, type check, unit tests, build image, integration tests, security scan, publish artifact. Cache dependencies. Run in parallel where possible. Keep the whole run short (aim for minutes).

Template (check that action versions are current before use):

```yaml
name: ci
on:
  pull_request:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4          # verify latest major version
      - uses: astral-sh/setup-uv@v5        # verify latest major version
      - run: uv sync --frozen
      - run: uv run ruff check .
      - run: uv run ruff format --check .
      - run: uv run pytest -q --maxfail=1
```

Add an eval job for ML/LLM projects that runs the fast eval set and fails on regression against the stored baseline.

### Releases
- **Staging first**, then production. Production deploys need explicit human approval.
- Strategy by risk: rolling update (default), blue-green (fast switch back), canary (small share of traffic, watch metrics, then widen), feature flags for behavior changes, shadow mode for new models.
- Define automatic rollback triggers (error rate, latency, quality proxy) before the release.
- Keep the previous version deployable with one command.

### Database migrations
Use **expand / contract**: (1) add new columns/tables, (2) deploy code that writes both, (3) backfill, (4) switch reads, (5) later remove the old. Never make a breaking schema change in the same release as the code that needs it. Never run migrations on a non-local database without approval and a backup.

### Rollback runbook (write one per service)
1. How to see what is deployed (version, model id, prompt version).
2. The exact command to roll back.
3. How to confirm recovery (health check, dashboard, test request).
4. Who to tell, and where to record the incident.

### Metrics worth measuring (never claim without data)
DORA: deployment frequency, lead time for changes, change failure rate, time to restore service. Track them; don't quote targets as achievements.

### Cloud and GPU basics
- Infrastructure as code (Terraform or Pulumi, or the project's choice). No manual console changes for anything lasting.
- Separate accounts/projects for dev, staging and prod; least-privilege roles; no long-lived keys where workload identity exists.
- GPUs are the biggest cost. Use spot/preemptible instances for training with checkpoints; shut down idle instances; set budgets and alerts; right-size before scaling out.
- Tag resources with owner and project. Review monthly cost by tag.
- Cloud-neutral by default; when on Google Cloud, see the Google skills in `INSTALL.md`.

### Scripts and scheduling
- Scripts take arguments, print what they will do, support `--dry-run` for anything destructive, and exit non-zero on failure.
- Use cron/Cloud Scheduler/Airflow for schedules, with alerts on failure and on missed runs.
- Log with timestamps; keep logs free of secrets and personal data.

---

## Part D. Documentation and handoff

Every deliverable has, in this order:
1. **README:** what it is, how to install, how to run, how to test (commands that work from a clean checkout).
2. **Design note or ADR** for non-obvious decisions (template in `roles/genai.md`).
3. **Model/data card** for models and datasets.
4. **Runbook** for anything that runs in production.
5. **Changelog** entry for behavior changes.

Write for the next person who has no context. Keep it short; link instead of repeating. Update docs in the same change as the code.

## Debugging routine (when something fails)

1. **Reproduce:** get a command or test that fails every time.
2. **Localize:** bisect (git bisect, comment out halves, log at boundaries) to the smallest failing area.
3. **Reduce:** shrink the input and the code to a minimal case.
4. **Fix** the root cause, not the symptom.
5. **Guard:** add a test that would have caught it, and a line in `LESSONS.md` if it was an agent mistake.

Read the actual error message and stack trace in full before guessing. Change one thing at a time.
