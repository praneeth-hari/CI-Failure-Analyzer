import random
from collections import Counter
from typing import Any


def pick_sample(
    rows: list[dict[str, Any]],
    repo_quota: dict[str, int],
    max_per_run: int = 2,
    max_per_job: int = 6,
    seed: int = 42,
) -> list[str]:
    """Deterministic, diversity-capped sample.

    rows: dicts with keys key, repo, run_id, job_name. Returns sorted keys.
    A repo missing from repo_quota contributes nothing.
    """
    ordered = sorted(rows, key=lambda r: r["key"])
    random.Random(seed).shuffle(ordered)
    per_repo: Counter = Counter()
    per_run: Counter = Counter()
    per_job: Counter = Counter()
    picked: list[str] = []
    for r in ordered:
        repo = r["repo"]
        job_key = (repo, r["job_name"])
        if per_repo[repo] >= repo_quota.get(repo, 0):
            continue
        if per_run[r["run_id"]] >= max_per_run:
            continue
        if per_job[job_key] >= max_per_job:
            continue
        picked.append(r["key"])
        per_repo[repo] += 1
        per_run[r["run_id"]] += 1
        per_job[job_key] += 1
    return sorted(picked)

