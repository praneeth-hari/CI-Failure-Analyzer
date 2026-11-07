import httpx

from app.core.config import settings


def main() -> None:
    headers = {
        "Authorization": f"Bearer {settings.github_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    url = "https://api.github.com/repos/fastapi/fastapi/actions/runs"
    resp = httpx.get(
        url,
        headers=headers,
        params={"status": "failure", "per_page": 5},
        timeout=30,
    )
    resp.raise_for_status()
    print(
        "rate limit remaining:",
        resp.headers.get("x-ratelimit-remaining"),
        "of",
        resp.headers.get("x-ratelimit-limit"),
    )
    data = resp.json()
    print("failed runs found (total):", data["total_count"])
    for run in data["workflow_runs"]:
        print(run["id"], run["name"], run["event"], run["head_sha"][:7], run["created_at"])


if __name__ == "__main__":
    main()
