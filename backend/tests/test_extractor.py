from app.ingestion.extractor import (
    extract_evidence,
    gate_failed_upstream_jobs,
    is_gate_job,
)


def make_log(lines):
    return "\n".join("2026-11-06T01:28:08.7352193Z " + line for line in lines)


def test_coverage_failure_is_found_and_noise_dropped():
    rows = [f"docs_src/mod{i}/file.py    10    0   100%" for i in range(60)]
    lines = [
        "##[group]Run coverage report",
        "coverage report --fail-under=100",
        "##[endgroup]",
        *rows,
        "docs_src/query_params/tutorial008_an_py310.py    7    7    0%   1-30",
        "-" * 60,
        "TOTAL    38316      7    99%",
        "Coverage failure: total of 99 is less than fail-under=100",
        "##[error]Process completed with exit code 2.",
    ]
    ev = extract_evidence(make_log(lines))
    text = ev.as_text()
    assert "Coverage failure" in text
    assert "tutorial008" in text
    assert "100%" not in text
    assert ev.step_header == "Run coverage report"
    assert ev.error_marker_line == len(lines)


def test_traceback_in_gate_job_is_captured():
    lines = [
        "##[group]Run python -m normalize_needed_jobs_status",
        "shell: bash",
        "##[endgroup]",
        "Some of the required to succeed jobs failed",
        "Traceback (most recent call last):",
        '  File "/x/normalize.py", line 277, in <module>',
        "    sys.exit(main(sys.argv))",
        "KeyError: 'abandoned'",
        "##[error]Process completed with exit code 1.",
    ]
    text = extract_evidence(make_log(lines)).as_text()
    assert "Traceback" in text
    assert "KeyError: 'abandoned'" in text


def test_gate_job_points_to_failing_upstream_job():
    log = make_log(["\u274c pre-commit \u2192 \U0001F534 failure [required to succeed]"])
    assert gate_failed_upstream_jobs(log) == ["pre-commit"]
    assert is_gate_job("pre-commit-alls-green")
    assert not is_gate_job("pre-commit")
    assert not is_gate_job("coverage-combine")


def test_timestamps_and_ansi_stripped_and_line_numbers_kept():
    lines = [
        "##[group]Run pytest",
        "##[endgroup]",
        "ok",
        "\x1b[31mFAILED\x1b[0m tests/test_a.py::test_x - assert 1 == 2",
        "##[error]Process completed with exit code 1.",
    ]
    ev = extract_evidence(make_log(lines))
    assert dict(ev.lines)[4] == "FAILED tests/test_a.py::test_x - assert 1 == 2"
    assert ev.step_header == "Run pytest"


def test_log_without_error_marker_falls_back_to_tail():
    ev = extract_evidence(make_log([f"line {i}" for i in range(500)]))
    assert ev.error_marker_line is None
    assert ev.lines[-1][1] == "line 499"


def test_output_is_capped():
    lines = (
        ["##[group]Run x", "##[endgroup]"]
        + [f"ERROR something {i}" for i in range(2000)]
        + ["##[error]Process completed with exit code 1."]
    )
    ev = extract_evidence(make_log(lines), max_lines=100)
    assert len(ev.lines) <= 100
    assert ev.lines[0][1] == "ERROR something 0"
    assert ev.lines[-1][1].startswith("##[error]")
