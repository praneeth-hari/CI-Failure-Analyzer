from app.ingestion.logs import is_relevant_workflow


def test_real_failures_are_relevant():
    for name in ["Test", "pre-commit", "Build Docs", "Test Redistribute"]:
        assert is_relevant_workflow(name)


def test_noise_workflows_are_ignored():
    for name in [
        "Smokeshow",
        "Add to Project",
        "uv in /. for Pillow - Update #1645660070",
        "pip in /. for requests - Update #12",
    ]:
        assert not is_relevant_workflow(name)
