import json
import random
import sys
from collections import Counter

from sqlalchemy import select

from app.analysis.labeling import load_labels, next_unlabeled, remove_label, save_label
from app.analysis.labels import LABELS
from app.core.config import ROOT_DIR
from app.db.models import FailureCase, Job, Repository, WorkflowRun
from app.db.session import SessionLocal

GOLD = ROOT_DIR / "eval" / "gold_v1.json"
LABELS_FILE = ROOT_DIR / "eval" / "gold_v1_labels.json"
SHOW_LINES = 60
MAX_WIDTH = 200


def fetch_case(session, key):
    owner_repo, job_id = key.rsplit(":", 1)
    owner, name = owner_repo.split("/", 1)
    return session.execute(
        select(FailureCase, Job, WorkflowRun, Repository)
        .join(Job, Job.id == FailureCase.job_id)
        .join(WorkflowRun, WorkflowRun.id == Job.run_id)
        .join(Repository, Repository.id == WorkflowRun.repo_id)
        .where(
            Repository.owner == owner,
            Repository.name == name,
            Job.github_job_id == int(job_id),
        )
    ).first()


def print_definitions(names):
    print()
    for i, name in enumerate(names, 1):
        print(f"{i}. {name}: {LABELS[name]}")
    print()


def print_stats(labels, total):
    counts = Counter(v["label"] for v in labels.values())
    print(f"\nlabeled {len(labels)} of {total}")
    for name in LABELS:
        print(f"  {name}: {counts.get(name, 0)}")


def show(case, done, total, full):
    fc, job, run, repo = case
    lines = fc.evidence_text.split("\n")
    hidden = 0
    if not full and len(lines) > SHOW_LINES:
        hidden = len(lines) - SHOW_LINES
        lines = lines[-SHOW_LINES:]
    print("\n" + "=" * 100)
    print(
        f"[{done}/{total} labeled]  {repo.owner}/{repo.name}  |  job: {job.name}"
        f"  |  workflow: {run.workflow_name}"
    )
    print(
        f"step: {fc.step_header or '(unknown)'}  |  error line: {fc.error_marker_line}"
        f"  |  log: {fc.log_bytes / 1048576:.1f} MB"
    )
    print("-" * 100)
    if hidden:
        print(f"... {hidden} earlier evidence lines hidden (type f to see all) ...")
    for line in lines:
        print(line[:MAX_WIDTH])
    print("-" * 100)
    print("  ".join(f"{i}={n}" for i, n in enumerate(LABELS, 1)))
    print("number [+ optional note] | ? definitions | f full | s skip | b undo | q quit")


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    keys = json.loads(GOLD.read_text(encoding="utf-8"))["keys"]
    if "--stats" in sys.argv:
        print_stats(load_labels(LABELS_FILE), len(keys))
        return
    order = list(keys)
    random.Random(0).shuffle(order)
    names = list(LABELS)
    print_definitions(names)
    skipped: set[str] = set()
    history: list[str] = []
    with SessionLocal() as session:
        while True:
            labels = load_labels(LABELS_FILE)
            key = next_unlabeled(order, labels, skipped)
            if key is None:
                if skipped:
                    print(f"{len(skipped)} skipped case(s) left - showing them again.")
                    skipped.clear()
                    continue
                print("All cases labeled.")
                print_stats(labels, len(keys))
                return
            case = fetch_case(session, key)
            if case is None:
                print(f"missing in database: {key}")
                skipped.add(key)
                continue
            show(case, len(labels), len(order), full=False)
            while True:
                raw = input("label> ").strip()
                head, _, rest = raw.partition(" ")
                cmd = head.lower()
                if cmd.isdigit() and 1 <= int(cmd) <= len(names):
                    save_label(LABELS_FILE, key, names[int(cmd) - 1], rest.strip())
                    history.append(key)
                    break
                if cmd == "s":
                    skipped.add(key)
                    break
                if cmd == "f":
                    show(case, len(labels), len(order), full=True)
                elif cmd == "?":
                    print_definitions(names)
                elif cmd == "b":
                    if history:
                        undone = history.pop()
                        remove_label(LABELS_FILE, undone)
                        print(f"undid {undone}")
                        break
                    print("nothing to undo")
                elif cmd == "q":
                    print_stats(load_labels(LABELS_FILE), len(keys))
                    return
                else:
                    print("type a number 1-9, or ? f s b q")


if __name__ == "__main__":
    try:
        main()
    except (EOFError, KeyboardInterrupt):
        print("\nstopped - progress is saved.")
