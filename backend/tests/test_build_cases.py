from datetime import datetime, timezone

from sqlalchemy import delete, select

import app.analysis.cases as cases_module
from app.analysis.cases import build_cases, read_log
from app.db.models import FailureCase, Job, Repository, WorkflowRun
from app.db.session import SessionLocal

LOG = (
    "\n".join(
        [
            "2026-11-06T10:00:00.0000000Z ##[group]Run pytest",
            "2026-11-06T10:00:01.0000000Z FAILED tests/test_x.py::test_a - assert 1 == 2",
            "2026-11-06T10:00:02.0000000Z E   assert 1 == 2",
            "2026-11-06T10:00:03.0000000Z ##[error]Process completed with exit code 1.",
        ]
    )
    + "\n"
)


def test_build_cases_is_idempotent_and_flags_gates(tmp_path):
    log_file = tmp_path / "job.log"
    log_file.write_text(LOG, encoding="utf-8")
    with SessionLocal() as session:
        repo = Repository(owner="test-owner", name="test-build")
        session.add(repo)
        session.flush()
        run = WorkflowRun(
            repo_id=repo.id,
            github_run_id=1,
            run_attempt=1,
            workflow_name="Test",
            event="push",
            head_sha="d" * 40,
            html_url="https://example.test",
            github_created_at=datetime(2026, 11, 6, tzinfo=timezone.utc),
        )
        session.add(run)
        session.flush()
        job_ids = []
        for gid, jname in ((1, "unit-tests"), (2, "test-alls-green")):
            job = Job(
                run_id=run.id,
                github_job_id=gid,
                name=jname,
                conclusion="failure",
                log_path=str(log_file),
            )
            session.add(job)
            session.flush()
            job_ids.append(job.id)
        session.commit()
        try:
            first = build_cases(session, "test-owner", "test-build")
            second = build_cases(session, "test-owner", "test-build")
            assert first["built"] == 2
            assert second["built"] == 0
            gate_flags = {
                j.name: fc.is_gate
                for fc, j in session.execute(
                    select(FailureCase, Job).join(Job, Job.id == FailureCase.job_id)
                ).all()
                if j.id in job_ids
            }
            assert gate_flags == {"unit-tests": False, "test-alls-green": True}
        finally:
            session.rollback()
            session.execute(delete(FailureCase).where(FailureCase.job_id.in_(job_ids)))
            session.execute(delete(Job).where(Job.id.in_(job_ids)))
            session.execute(delete(WorkflowRun).where(WorkflowRun.id == run.id))
            session.execute(delete(Repository).where(Repository.id == repo.id))
            session.commit()


def test_read_log_reads_only_the_tail_of_huge_files(tmp_path, monkeypatch):
    big = tmp_path / "big.log"
    big.write_text("".join(f"line {i}\n" for i in range(1000)), encoding="utf-8")
    monkeypatch.setattr(cases_module, "MAX_READ_BYTES", 100)
    text, size = read_log(big)
    assert size == big.stat().st_size
    assert len(text) < 200
    assert text.endswith("line 999\n")
    assert text.split("\n")[0].startswith("line ")

