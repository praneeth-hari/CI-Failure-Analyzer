# Role: Data Engineer and Data Scientist

Read this for data pipelines, data quality, embedding/vector ingestion, exploratory analysis, experiments and A/B tests. Rules in `AGENTS.md` always apply.

## 1. Pipeline principles

- **Idempotent:** running a job twice gives the same result. Use upserts or overwrite-by-partition, never blind appends.
- **Re-runnable by date:** every job takes a run date/partition parameter, so backfills are the same code as daily runs.
- **Small steps:** extract, validate, transform, load as separate stages with stored intermediate outputs you can inspect.
- **Immutable raw data:** keep raw input untouched; derive everything else from it.
- **Schema is a contract:** declare it, validate on read, and fail loudly on unexpected changes.
- **Retries with backoff** for network and API calls; dead-letter anything that keeps failing; never silently drop rows. Count rows in, rows out, rows rejected, and log them.
- **Secrets from the environment or a secret manager.** Never in code or config in git.
- Orchestrate with Airflow, Dagster, Prefect or a cloud scheduler (verify what the project already uses and keep to it).

## 2. Data quality checks (put them in the pipeline, not in a notebook)

| Check | Examples |
|---|---|
| Schema | columns, types, required fields |
| Completeness | null rate per column under a threshold |
| Uniqueness | primary key has no duplicates |
| Validity | ranges, allowed values, formats |
| Freshness | newest record is recent enough |
| Volume | row count within expected band vs last run |
| Consistency | joins don't drop or multiply rows unexpectedly |

Use Great Expectations, Pandera, Soda or dbt tests. A failed critical check stops the pipeline and alerts; a warning is logged and reviewed.

## 3. Ingestion for LLM and vector systems

1. Extract text with structure (headings, tables, page numbers). Check PDFs and scans visually on a sample.
2. Clean: remove boilerplate (headers, footers, navigation), fix encodings, drop empty documents.
3. Deduplicate exact and near-duplicate documents before chunking.
4. Detect and mask personal data before embedding if the data is sensitive.
5. Chunk (see `roles/genai.md`) and attach metadata: source id, URL or path, section, date, access level, content hash.
6. Embed in batches with rate-limit handling; store the embedding model name and version.
7. Upsert by content hash so unchanged documents are not re-embedded; delete vectors for deleted documents.
8. After each load, run a small retrieval test (known question must find known chunk).

## 4. Exploratory analysis (EDA)

- Start with the question, not the dataset.
- Check counts, missing data, distributions, outliers, duplicates, time coverage.
- Plot before modeling; label axes and units; include sample sizes.
- Write down findings as short statements with the number and how it was computed.
- Distinguish correlation from causation in the wording. Say "associated with", not "causes", unless the design supports causation.
- Keep a reproducible script or notebook that regenerates every figure from raw data.

## 5. Experiment design and statistics sanity checks

**Before the test**
- Define one primary metric, guardrail metrics (things that must not get worse), the unit of randomization, and the minimum effect worth detecting.
- Compute the needed sample size up front (power analysis). Fix the run length; don't stop early when it looks good.
- Randomize at the right unit (user, not request, if users see several requests).

**After the test**
- Check the split is balanced (sample ratio mismatch) before reading results.
- Report effect size with a confidence interval, not just a p-value.
- Adjust for multiple comparisons when checking many metrics or segments.
- Beware of peeking, novelty effects, and segment-hunting after the fact.
- For LLM changes, include quality (judge or human sample), latency, cost and safety metrics, not only clicks.

**Common traps:** Simpson's paradox, survivorship bias, selection bias, small samples, outliers driving means (use medians or trimmed means), time-of-week effects.

## 6. SQL and dataframes

- Prefer SQL/dbt for transformations in the warehouse; pandas/Polars for exploration; Spark for data that doesn't fit one machine.
- Select only needed columns, filter early, and check join keys for uniqueness before joining.
- Test queries on a small slice first; look at `EXPLAIN` for slow ones.
- Name things clearly; comment the why, not the what.
- Never `SELECT *` into a production table.

## 7. Big data tools (generic guidance)

**Spark**
- Use DataFrames, not RDDs. Avoid Python UDFs where a built-in function exists.
- Partition by a column used for filtering; avoid many tiny files; check for skewed keys.
- Cache only data reused multiple times. Broadcast small tables in joins.
- Look at the Spark UI for shuffles and skew before adding more machines.

**Kafka / streaming**
- Choose keys deliberately (they decide ordering and partitioning).
- Design consumers to be idempotent, since delivery can repeat.
- Monitor consumer lag; handle poison messages with a dead-letter topic.
- Define event schemas with versioning (Avro/Protobuf/JSON Schema and a registry).

## 8. Storage and formats

- Columnar formats (Parquet) with compression for analytics; partition by date or another common filter.
- Table formats (Delta, Iceberg, Hudi) when you need updates, time travel or schema evolution.
- Keep a data catalog or at least a README per dataset: owner, source, refresh schedule, schema, known issues.

## 9. Governance and privacy

- Know which columns hold personal or regulated data. Mask, hash or drop them as early as possible.
- Apply least-privilege access; log who reads sensitive tables.
- Respect retention and deletion rules (including deleting from derived data and vector stores).
- Don't copy production personal data to laptops, notebooks or external services without approval.

## 10. If the project is on Google Cloud

Google publishes agent skills for BigQuery, Airflow/Cloud Composer, dbt and other data services (see `INSTALL.md`). If those are installed, prefer them for service-specific commands, and keep this file for general rules. Pick only the few you need.

## Output checklist for a data task

- [ ] Source, grain (what one row means), and refresh schedule stated
- [ ] Job is idempotent and re-runnable by date
- [ ] Quality checks added, with a failure behavior
- [ ] Row counts logged at each stage
- [ ] Sample output inspected by eye
- [ ] No secrets or personal data exposed
- [ ] Short README or docstring for the next person
