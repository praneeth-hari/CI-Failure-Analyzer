import re

REDACTED = "[REDACTED]"

PATTERNS = [
    ("github_token", re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{36,}\b")),
    ("github_pat", re.compile(r"\bgithub_pat_[A-Za-z0-9_]{22,}\b")),
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("slack_token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b")),
    (
        "private_key",
        re.compile(
            r"-----BEGIN [A-Z ]*PRIVATE KEY-----.*?-----END [A-Z ]*PRIVATE KEY-----",
            re.DOTALL,
        ),
    ),
    ("bearer", re.compile(r"\b(Bearer)\s+[A-Za-z0-9\-._~+/]{20,}=*")),
    ("jwt", re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b")),
    (
        "assignment",
        re.compile(
            r"""\b([A-Z][A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_?KEY|ACCESS_?KEY)[A-Z0-9_]*)=(?!\[REDACTED\])["']?[^\s"']{6,}["']?"""
        ),
    ),
]


def redact(text: str) -> tuple[str, dict[str, int]]:
    counts: dict[str, int] = {}

    def bump(name: str) -> None:
        counts[name] = counts.get(name, 0) + 1

    for name, pattern in PATTERNS:
        if name == "assignment":

            def repl(match: re.Match, name: str = name) -> str:
                bump(name)
                return f"{match.group(1)}={REDACTED}"

        elif name == "bearer":

            def repl(match: re.Match, name: str = name) -> str:
                bump(name)
                return f"{match.group(1)} {REDACTED}"

        else:

            def repl(match: re.Match, name: str = name) -> str:
                bump(name)
                return REDACTED

        text = pattern.sub(repl, text)
    return text, counts
