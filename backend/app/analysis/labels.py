LABELS: dict[str, str] = {
    "test_failure": "A test assertion or test error failed (the code under test or the test itself is wrong).",
    "lint_format": "A linter or formatter check failed (ruff, black, pre-commit, prek, style).",
    "type_check": "A static type checker failed (mypy, pyright).",
    "dependency_build": "Installing dependencies or building/compiling failed (resolver error, wheel build, compile error, import error during setup).",
    "infra_network": "CI environment problem unrelated to the code change: runner issue, timeout, network or download error, rate limit, cache or permission (403) error.",
    "coverage_threshold": "Coverage or another quality threshold was not met (fail-under, benchmark, size limit).",
    "config_workflow": "The workflow or project configuration itself is wrong (bad YAML, missing secret or input, wrong command).",
    "docs_build": "Documentation build or link check failed.",
    "other_unclear": "Cannot tell from the evidence, or does not fit any other class.",
}
