import sys
from pathlib import Path

from app.ingestion.extractor import extract_evidence, gate_failed_upstream_jobs


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = Path(sys.argv[1]).read_text(encoding="utf-8", errors="replace")
    ev = extract_evidence(text)
    print(f"step: {ev.step_header}")
    print(f"error marker at line: {ev.error_marker_line}; evidence lines: {len(ev.lines)}")
    gate = gate_failed_upstream_jobs(text)
    if gate:
        print(f"gate says failed upstream jobs: {gate}")
    print(ev.as_text())


if __name__ == "__main__":
    main()
