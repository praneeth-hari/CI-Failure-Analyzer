from sqlalchemy import delete, select

from app.db.models import Repository, WorkflowRun
from app.db.session import SessionLocal
from app.ingestion.collector import collect_failed_runs


class FakeClient:
    def iter_failed_runs(self, owner, repo, created_since):
        yield {
            "id": 999000111,
            "run_attempt": 1,
            "name": "Test",
            "event": "push",
            "head_branch": "main",
            "head_sha": "a" * 40,
            "conclusion": "failure",
            "html_url": "https://example.test/run/1",
            "run_started_at": "2026-11-06T11:00:00Z",
            "created_at": "2026-11-06T10:59:00Z",
        }


def test_collecting_twice_does_not_duplicate():
    with SessionLocal() as session:
        try:
            first = collect_failed_runs(session, FakeClient(), "test-owner", "test-repo")
            second = collect_failed_runs(session, FakeClient(), "test-owner", "test-repo")
            assert first["inserted"] == 1
            assert second["inserted"] == 0
        finally:
            repo = session.scalar(
                select(Repository).where(
                    Repository.owner == "test-owner", Repository.name == "test-repo"
                )
            )
            if repo:
                session.execute(delete(WorkflowRun).where(WorkflowRun.repo_id == repo.id))
                session.execute(delete(Repository).where(Repository.id == repo.id))
                session.commit()
