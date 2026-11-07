from app.ingestion.redact import redact


def test_redacts_github_tokens():
    text = "using ghp_" + "a" * 36 + " and github_pat_" + "B" * 30
    clean, counts = redact(text)
    assert "ghp_" not in clean
    assert "github_pat_" not in clean
    assert counts["github_token"] == 1
    assert counts["github_pat"] == 1


def test_redacts_aws_key():
    clean, counts = redact("key is AKIA" + "ABCDEFGHIJKLMNOP here")
    assert "AKIA" not in clean
    assert counts["aws_access_key"] == 1


def test_redacts_private_key_block():
    text = "-----BEGIN " + "RSA PRIVATE KEY-----\nMIIabc\n-----END RSA PRIVATE KEY-----"
    clean, counts = redact("before\n" + text + "\nafter")
    assert "MIIabc" not in clean
    assert clean.startswith("before") and clean.endswith("after")
    assert counts["private_key"] == 1


def test_redacts_bearer_token():
    clean, _ = redact("Authorization: Bearer " + "x" * 30)
    assert clean == "Authorization: Bearer [REDACTED]"


def test_redacts_env_assignment_but_keeps_name():
    clean, counts = redact("DATABASE_PASSWORD=hunter2hunter2 done")
    assert clean == "DATABASE_PASSWORD=[REDACTED] done"
    assert counts["assignment"] == 1


def test_token_assignment_is_counted_once():
    clean, counts = redact("GITHUB_TOKEN=ghp_" + "c" * 36)
    assert clean == "GITHUB_TOKEN=[REDACTED]"
    assert counts == {"github_token": 1}


def test_normal_error_messages_are_untouched():
    samples = [
        "AttributeError: module 'numpy' has no attribute 'float_'",
        "TokenError: invalid token supplied",
        "FAILED tests/test_x.py::test_y - assert 1 == 2",
        "ImportError: cannot import name 'SecretStr' from 'pydantic'",
    ]
    for line in samples:
        clean, counts = redact(line)
        assert clean == line
        assert counts == {}
