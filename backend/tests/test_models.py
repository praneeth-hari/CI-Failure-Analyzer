from app.db import models  # noqa: F401
from app.db.base import Base


def test_tables_registered():
    assert {"repositories", "workflow_runs", "jobs"} <= set(Base.metadata.tables)


def test_workflow_run_is_unique_per_repo_run_and_attempt():
    table = Base.metadata.tables["workflow_runs"]
    unique_sets = [
        {c.name for c in con.columns}
        for con in table.constraints
        if con.__class__.__name__ == "UniqueConstraint"
    ]
    assert {"repo_id", "github_run_id", "run_attempt"} in unique_sets
