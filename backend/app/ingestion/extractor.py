import re
from dataclasses import dataclass

TIMESTAMP = re.compile(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z ?")
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
COVERAGE_OK_ROW = re.compile(r"\s100%\s*$")
SIGNAL = re.compile(
    r"(?i:error|exception|traceback|fatal|failed|failure|assert|cannot|could not"
    r"|no such file|not found|denied|timed out|timeout|exit code|fail-under)"
    r"|^E {2,}|^(FAILED|ERROR) |\s0%(\s|$)|^\s+File \".*\", line \d+"
)
GATE_JOB = re.compile(r"alls-green", re.IGNORECASE)
GATE_FAILED_ROW = re.compile(r"\u274c\s+(.+?)\s+\u2192\s+\S+\s+failure")


@dataclass
class Evidence:
    step_header: str | None
    lines: list[tuple[int, str]]
    error_marker_line: int | None

    def as_text(self) -> str:
        return "\n".join(f"{n}: {t}" for n, t in self.lines)


def is_gate_job(job_name: str) -> bool:
    return bool(GATE_JOB.search(job_name))


def gate_failed_upstream_jobs(log_text: str) -> list[str]:
    return [m.group(1) for m in GATE_FAILED_ROW.finditer(log_text)]


def extract_evidence(
    log_text: str, max_lines: int = 120, context: int = 2, tail: int = 10
) -> Evidence:
    cleaned = [
        ANSI.sub("", TIMESTAMP.sub("", raw)).rstrip() for raw in log_text.splitlines()
    ]
    if not cleaned:
        return Evidence(None, [], None)

    error_idx = next(
        (i for i, t in enumerate(cleaned) if t.startswith("##[error]")), None
    )
    end = error_idx if error_idx is not None else len(cleaned) - 1

    start = max(0, end - 150)
    for i in range(end, -1, -1):
        if cleaned[i].startswith("##[endgroup]"):
            start = i + 1
            break

    header = None
    for i in range(start - 1, -1, -1):
        if cleaned[i].startswith("##[group]"):
            header = cleaned[i][len("##[group]"):]
            break

    if end - start < 5:
        start = max(0, end - 40)

    window = [
        (i + 1, cleaned[i])
        for i in range(start, end + 1)
        if cleaned[i].strip() and not COVERAGE_OK_ROW.search(cleaned[i])
    ]

    keep: set[int] = set()
    for pos, (_, text) in enumerate(window):
        if SIGNAL.search(text):
            keep.update(range(max(0, pos - context), min(len(window), pos + context + 1)))
    keep.update(range(max(0, len(window) - tail), len(window)))

    ordered = sorted(keep)
    if len(ordered) > max_lines:
        head = max_lines // 2
        ordered = ordered[:head] + ordered[-(max_lines - head):]

    return Evidence(
        header,
        [window[p] for p in ordered],
        error_idx + 1 if error_idx is not None else None,
    )
