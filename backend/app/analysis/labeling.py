import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.analysis.labels import LABELS


def load_labels(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    os.replace(tmp, path)  # atomic: a crash never leaves a half-written file


def save_label(path: Path, key: str, label: str, notes: str = "") -> None:
    if label not in LABELS:
        raise ValueError(f"unknown label: {label}")
    data = load_labels(path)
    data[key] = {
        "label": label,
        "notes": notes,
        "labeled_at": datetime.now(timezone.utc).isoformat(),
    }
    _write(path, data)


def remove_label(path: Path, key: str) -> None:
    data = load_labels(path)
    if key in data:
        del data[key]
        _write(path, data)


def next_unlabeled(keys, labels, skipped=()):
    for key in keys:
        if key not in labels and key not in skipped:
            return key
    return None
