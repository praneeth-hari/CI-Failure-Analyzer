import re
import sys
from datetime import datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import ROOT_DIR
from app.db.models import Job, Repository, WorkflowRun
from app.ingestion.redact import redact

LOG_DIR = ROOT_DIR / "data" / "raw_logs"
IGNORED_WORKFLOWS = {
    "Smokeshow",
    "Add to Project",
    "Labeler",
    "Latest Changes",
    "Issue Manager",
}
DEPENDABOT_NAME = re.compile(r"^(uv|pip|npm|github-actions|docker|cargo) in ")


def is_relevant_workflow(name: str) -> bool:
    return name not in IGNORED_WORKFLOWS and not DEPENDABOT_NAME.match(name)


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value else None


def _process_run(
    session: Session,
    client: Any,
    owner: str,
    name: str,
    run: WorkflowRun,
    existing: dict[int, Job],
    stats: dict[str, int],
) -> None:
    for gj in client.list_jobs(owner, name, run.github_run_id):
        job = existing.get(gj["id"])
        if job is None:
            job = Job(
                run_id=run.id,
                github_job_id=gj["id"],
                name=gj["name"],
                conclusion=gj.get("conclusion"),
                started_at=_dt(gj.get("started_at")),
                completed_at=_dt(gj.get("completed_at")),
            )
            session.add(job)
            session.flush()
            stats["jobs"] += 1
        if job.conclusion == "failure" and not job.log_path:
            text = client.download_job_log(owner, name, job.github_job_id)
            if text is None:
                stats["expired"] += 1
                continue
            clean, counts = redact(text)
            path = (
                LOG_DIR
                / owner
                / name
                / str(run.github_run_id)
                / f"{job.github_job_id}.log"
            )
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(clean, encoding="utf-8", newline="")
            job.log_path = str(path.relative_to(ROOT_DIR))
            stats["logs"] += 1
            stats["redactions"] += sum(counts.values())
    session.commit()


def collect_logs(
    session: Session, client: Any, owner: str, name: str, limit: int = 10
) -> dict[str, int]:
    repo = session.scalar(
        select(Repository).where(Repository.owner == owner, Repository.name == name)
    )
    if repo is None:
        raise ValueError(f"{owner}/{name} has no collected runs yet")

    runs = session.scalars(
        select(WorkflowRun)
        .where(WorkflowRun.repo_id == repo.id)
        .order_by(WorkflowRun.github_created_at.desc())
    ).all()

    stats = {"runs": 0, "jobs": 0, "logs": 0, "expired": 0, "redactions": 0, "skipped": 0}
    for run in runs:
        if stats["runs"] >= limit:
            break
        if not is_relevant_workflow(run.workflow_name):
            continue
        existing = {
            j.github_job_id: j
            for j in session.scalars(select(Job).where(Job.run_id == run.id))
        }
        if existing and all(
            j.conclusion != "failure" or j.log_path for j in existing.values()
        ):
            continue

        stats["runs"] += 1
        run_id = run.github_run_id
        try:
            _process_run(session, client, owner, name, run, existing, stats)
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            session.rollback()
            stats["skipped"] += 1
            reason = (
                exc.response.status_code
                if isinstance(exc, httpx.HTTPStatusError)
                else type(exc).__name__
            )
            print(f"skipped run {run_id}: {reason}", file=sys.stderr)
    return stats
