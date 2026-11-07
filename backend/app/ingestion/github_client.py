from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

API = "https://api.github.com"
RETRY_STATUS = {429, 500, 502, 503, 504}


class RateLimitError(RuntimeError):
    pass


def _should_retry(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRY_STATUS
    return False


class GitHubClient:
    def __init__(self, token: str | None = None) -> None:
        self._http = httpx.Client(
            base_url=API,
            headers={
                "Authorization": f"Bearer {token or settings.github_token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            timeout=30,
        )

    def close(self) -> None:
        self._http.close()

    @retry(
        retry=retry_if_exception(_should_retry),
        stop=stop_after_attempt(4),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        reraise=True,
    )
    def _get(self, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
        resp = self._http.get(path, params=params)
        if resp.status_code == 403 and resp.headers.get("x-ratelimit-remaining") == "0":
            raise RateLimitError("GitHub rate limit reached; try again after it resets")
        resp.raise_for_status()
        return resp

    def iter_failed_runs(
        self, owner: str, repo: str, created_since: str, max_pages: int = 10
    ) -> Iterator[dict[str, Any]]:
        for page in range(1, max_pages + 1):
            resp = self._get(
                f"/repos/{owner}/{repo}/actions/runs",
                params={
                    "status": "failure",
                    "created": f">={created_since}",
                    "per_page": 100,
                    "page": page,
                },
            )
            runs = resp.json()["workflow_runs"]
            if not runs:
                return
            yield from runs
            if len(runs) < 100:
                return
