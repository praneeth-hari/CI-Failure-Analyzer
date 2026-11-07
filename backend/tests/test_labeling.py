import pytest

from app.analysis.labeling import load_labels, next_unlabeled, remove_label, save_label


def test_save_load_and_remove_label(tmp_path):
    path = tmp_path / "labels.json"
    assert load_labels(path) == {}
    save_label(path, "o/r:1", "test_failure", "note")
    save_label(path, "o/r:2", "lint_format")
    labels = load_labels(path)
    assert labels["o/r:1"]["label"] == "test_failure"
    assert labels["o/r:1"]["notes"] == "note"
    remove_label(path, "o/r:1")
    assert "o/r:1" not in load_labels(path)
    assert "o/r:2" in load_labels(path)


def test_unknown_label_is_rejected(tmp_path):
    path = tmp_path / "labels.json"
    with pytest.raises(ValueError):
        save_label(path, "o/r:1", "made_up")
    assert not path.exists()


def test_next_unlabeled_skips_done_and_skipped():
    keys = ["a", "b", "c"]
    assert next_unlabeled(keys, {}) == "a"
    assert next_unlabeled(keys, {"a": {}}, skipped={"b"}) == "c"
    assert next_unlabeled(keys, {"a": {}, "c": {}}, skipped={"b"}) is None
