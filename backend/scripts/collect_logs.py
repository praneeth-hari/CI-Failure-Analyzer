import sys

from app.db.session import SessionLocal
from app.ingestion.github_client import GitHubClient
from app.ingestion.logs import collect_logs


def main() -> None:
    target = sys.argv[1] if len(sys.argv) > 1 else "fastapi/fastapi"
    limit = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    owner, name = target.split("/")
    client = GitHubClient()
    try:
        with SessionLocal() as session:
            stats = collect_logs(session, client, owner, name, limit)
    finally:
        client.close()
    print(f"{target}: {stats}")


if __name__ == "__main__":
    main()
