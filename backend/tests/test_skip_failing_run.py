from datetime import datetime, timezone

import httpx
from sqlalchemy import delete, select

from app.db.models import Repository, WorkflowRun
from app.db.session import SessionLocal
from app.ingestion.logs import collect_logs


class FlakyClient:
    def list_jobs(self, owner, repo, run_id):
        if run_id == 1:
            request = httpx.Request("GET", "https://api.github.com/x")
            response = httpx.Response(502, request=request)
            raise httpx.HTTPStatusError(
                "bad gateway", request=request, response=response
            )
        return []

    def download_job_log(self, owner, repo, job_id):
        return None


def test_one_failing_run_does_not_abort_the_batch():
    with SessionLocal() as session:
        repo = Repository(owner="test-owner", name="test-skip")
        session.add(repo)
        session.flush()
        for rid in (1, 2):
            session.add(
                WorkflowRun(
                    repo_id=repo.id,
                    github_run_id=rid,
                    run_attempt=1,
                    workflow_name="Test",
                    event="push",
                    head_sha="b" * 40,
                    html_url="https://example.test",
                    github_created_at=datetime(2026, 11, 6, tzinfo=timezone.utc),
                )
            )
        session.commit()
        try:
            stats = collect_logs(session, FlakyClient(), "test-owner", "test-skip")
            assert stats["skipped"] == 1
            assert stats["runs"] == 2
        finally:
            repo = session.scalar(
                select(Repository).where(
                    Repository.owner == "test-owner", Repository.name == "test-skip"
                )
            )
            if repo:
                session.execute(delete(WorkflowRun).where(WorkflowRun.repo_id == repo.id))
                session.execute(delete(Repository).where(Repository.id == repo.id))
                session.commit()

