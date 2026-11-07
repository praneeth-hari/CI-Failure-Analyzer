from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.config import ROOT_DIR
from app.db.models import FailureCase, Job, Repository, WorkflowRun
from app.ingestion.extractor import (
    extract_evidence,
    gate_failed_upstream_jobs,
    is_gate_job,
)

# Logs above this size are read from the tail only: the real error is near the end.
MAX_READ_BYTES = 10 * 1024 * 1024


def read_log(path: Path) -> tuple[str, int]:
    """Return (text, original_size_in_bytes). Huge files are read from the tail."""
    size = path.stat().st_size
    with path.open("rb") as f:
        if size > MAX_READ_BYTES:
            f.seek(size - MAX_READ_BYTES)
            data = f.read().split(b"\n", 1)[-1]  # drop the partial first line
        else:
            data = f.read()
    return data.decode("utf-8", errors="replace").replace("\r\n", "\n"), size


def build_cases(
    session: Session,
    owner: str | None = None,
    name: str | None = None,
    limit: int | None = None,
) -> dict[str, int]:
    stmt = (
        select(Job.id, Job.name, Job.log_path)
        .join(WorkflowRun, Job.run_id == WorkflowRun.id)
        .join(Repository, WorkflowRun.repo_id == Repository.id)
        .outerjoin(FailureCase, FailureCase.job_id == Job.id)
        .where(
            Job.conclusion == "failure",
            Job.log_path.is_not(None),
            FailureCase.id.is_(None),
        )
        .order_by(Job.id)
    )
    if owner and name:
        stmt = stmt.where(Repository.owner == owner, Repository.name == name)
    if limit:
        stmt = stmt.limit(limit)
    rows = session.execute(stmt).all()

    stats = {"built": 0, "gate": 0, "empty": 0, "missing_file": 0, "large": 0}
    for i, (job_id, job_name, log_path) in enumerate(rows, start=1):
        path = ROOT_DIR / log_path
        if not path.exists():
            stats["missing_file"] += 1
            continue
        text, size = read_log(path)
        if size > MAX_READ_BYTES:
            stats["large"] += 1
        evidence = extract_evidence(text)
        gate = is_gate_job(job_name)
        values: dict[str, Any] = {
            "job_id": job_id,
            "is_gate": gate,
            "step_header": evidence.step_header,
            "error_marker_line": evidence.error_marker_line,
            "evidence_text": evidence.as_text(),
            "evidence_line_count": len(evidence.lines),
            "log_bytes": size,
            "upstream_jobs": gate_failed_upstream_jobs(text) if gate else None,
        }
        stmt_ins = (
            insert(FailureCase)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["job_id"])
            .returning(FailureCase.id)
        )
        if session.execute(stmt_ins).first() is not None:
            stats["built"] += 1
            stats["gate"] += 1 if gate else 0
            stats["empty"] += 1 if not evidence.lines else 0
        if i % 50 == 0:
            session.commit()
    session.commit()
    return stats
