import json
from collections import Counter

from sqlalchemy import select

from app.analysis.sampling import pick_sample
from app.core.config import ROOT_DIR
from app.db.models import FailureCase, Job, Repository, WorkflowRun
from app.db.session import SessionLocal

VERSION = "gold_v1"
SEED = 42
QUOTAS = {"pydantic": 40, "pandas": 40, "fastapi": 25, "core": 25}
MAX_PER_RUN = 2
MAX_PER_JOB = 6


def main() -> None:
    with SessionLocal() as session:
        result = session.execute(
            select(
                Repository.owner,
                Repository.name,
                WorkflowRun.github_run_id,
                Job.name,
                Job.github_job_id,
            )
            .select_from(FailureCase)
            .join(Job, Job.id == FailureCase.job_id)
            .join(WorkflowRun, WorkflowRun.id == Job.run_id)
            .join(Repository, Repository.id == WorkflowRun.repo_id)
            .where(FailureCase.is_gate.is_(False))
        ).all()
    rows = [
        {
            "key": f"{owner}/{name}:{job_id}",
            "repo": name,
            "run_id": run_id,
            "job_name": job_name,
        }
        for owner, name, run_id, job_name, job_id in result
    ]
    keys = pick_sample(rows, QUOTAS, MAX_PER_RUN, MAX_PER_JOB, SEED)
    chosen = set(keys)
    per_repo = Counter(r["repo"] for r in rows if r["key"] in chosen)
    distinct_jobs = len({(r["repo"], r["job_name"]) for r in rows if r["key"] in chosen})
    out = ROOT_DIR / "eval" / f"{VERSION}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": VERSION,
        "seed": SEED,
        "quotas": QUOTAS,
        "max_per_run": MAX_PER_RUN,
        "max_per_job": MAX_PER_JOB,
        "keys": keys,
    }
    out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"candidates={len(rows)} picked={len(keys)} distinct_job_names={distinct_jobs}")
    print(dict(per_repo))
    print(f"wrote {out}")


if __name__ == "__main__":
    main()

