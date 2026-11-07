from collections import Counter

from app.analysis.sampling import pick_sample


def make_rows():
    rows = []
    for run in range(10):
        for j in range(5):
            rows.append({"key": f"a:{run}-{j}", "repo": "a", "run_id": run, "job_name": f"job{j}"})
    for i in range(30):
        rows.append({"key": f"b:{i}", "repo": "b", "run_id": 100 + i, "job_name": "same"})
    for i in range(5):
        rows.append({"key": f"c:{i}", "repo": "c", "run_id": 200 + i, "job_name": f"j{i}"})
    return rows


def test_pick_sample_respects_quota_and_caps():
    picked = pick_sample(make_rows(), {"a": 12, "b": 20}, max_per_run=2, max_per_job=6, seed=1)
    a_keys = [k for k in picked if k.startswith("a:")]
    b_keys = [k for k in picked if k.startswith("b:")]
    assert len(a_keys) == 12
    assert len(b_keys) == 6  # all share one job name, capped at 6
    per_run = Counter(k.split(":")[1].split("-")[0] for k in a_keys)
    assert max(per_run.values()) <= 2


def test_pick_sample_is_deterministic_and_order_independent():
    rows = make_rows()
    quota = {"a": 12, "b": 20}
    first = pick_sample(rows, quota, seed=7)
    again = pick_sample(list(reversed(rows)), quota, seed=7)
    assert first == again


def test_pick_sample_ignores_repos_without_quota():
    picked = pick_sample(make_rows(), {"a": 5}, seed=3)
    assert not any(k.startswith(("b:", "c:")) for k in picked)

