import pytest
from datetime import datetime, timezone
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError

from app.db.models import FailureCase, Job, Repository, WorkflowRun
from app.db.session import SessionLocal


def test_one_failure_case_per_job():
    with SessionLocal() as session:
        repo = Repository(owner="test-owner", name="test-cases")
        session.add(repo)
        session.flush()
        run = WorkflowRun(
            repo_id=repo.id,
            github_run_id=1,
            run_attempt=1,
            workflow_name="Test",
            event="push",
            head_sha="c" * 40,
            html_url="https://example.test",
            github_created_at=datetime(2026, 11, 6, tzinfo=timezone.utc),
        )
        session.add(run)
        session.flush()
        job = Job(run_id=run.id, github_job_id=1, name="test", conclusion="failure")
        session.add(job)
        session.flush()
        job_id = job.id
        try:
            session.add(
                FailureCase(
                    job_id=job_id,
                    evidence_text="E   assert 1 == 2",
                    evidence_line_count=1,
                    log_bytes=100,
                )
            )
            session.commit()
            session.add(
                FailureCase(
                    job_id=job_id,
                    evidence_text="duplicate",
                    evidence_line_count=1,
                    log_bytes=100,
                )
            )
            with pytest.raises(IntegrityError):
                session.commit()
        finally:
            session.rollback()
            session.execute(delete(FailureCase).where(FailureCase.job_id == job_id))
            session.execute(delete(Job).where(Job.id == job_id))
            session.execute(delete(WorkflowRun).where(WorkflowRun.id == run.id))
            session.execute(delete(Repository).where(Repository.id == repo.id))
            session.commit()

