import sys

from app.db.session import SessionLocal
from app.ingestion.collector import collect_failed_runs
from app.ingestion.github_client import GitHubClient


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "fastapi/fastapi"
    days = int(sys.argv[2]) if len(sys.argv) > 2 else 30
    owner, name = target.split("/")
    client = GitHubClient()
    try:
        with SessionLocal() as session:
            stats = collect_failed_runs(session, client, owner, name, days)
    finally:
        client.close()
    print(f"{target}: saw {stats['seen']} failed runs, saved {stats['inserted']} new")


if __name__ == "__main__":
    main()
