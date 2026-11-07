from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.db.models import Repository, WorkflowRun


def get_or_create_repository(session: Session, owner: str, name: str) -> Repository:
    repo = session.scalar(
        select(Repository).where(Repository.owner == owner, Repository.name == name)
    )
    if repo is None:
        repo = Repository(owner=owner, name=name)
        session.add(repo)
        session.flush()
    return repo


def _run_values(repo_id: int, run: dict[str, Any]) -> dict[str, Any]:
    started = run.get("run_started_at")
    return {
        "repo_id": repo_id,
        "github_run_id": run["id"],
        "run_attempt": run.get("run_attempt") or 1,
        "workflow_name": run.get("name") or "unknown",
        "event": run["event"],
        "branch": run.get("head_branch"),
        "head_sha": run["head_sha"],
        "conclusion": run.get("conclusion"),
        "html_url": run["html_url"],
        "run_started_at": datetime.fromisoformat(started) if started else None,
        "github_created_at": datetime.fromisoformat(run["created_at"]),
    }


def collect_failed_runs(
    session: Session, client: Any, owner: str, name: str, days: int = 30
) -> dict[str, int]:
    repo = get_or_create_repository(session, owner, name)
    since = (datetime.now(timezone.utc) - timedelta(days=days)).date().isoformat()
    seen = 0
    inserted = 0
    for run in client.iter_failed_runs(owner, name, since):
        seen += 1
        stmt = (
            insert(WorkflowRun)
            .values(**_run_values(repo.id, run))
            .on_conflict_do_nothing(
                index_elements=["repo_id", "github_run_id", "run_attempt"]
            )
        )
        result = session.execute(stmt.returning(WorkflowRun.id))
        inserted += 1 if result.first() is not None else 0
    session.commit()
    return {"seen": seen, "inserted": inserted}
