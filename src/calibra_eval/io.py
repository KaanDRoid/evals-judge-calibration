from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .models import Task


def load_tasks(directory: Path) -> list[Task]:
    tasks = []
    for path in sorted(directory.glob("*.json")):
        tasks.append(Task.from_dict(json.loads(path.read_text(encoding="utf-8"))))
    if not tasks:
        raise ValueError(f"No task JSON files found in {directory}")
    ids = [task.id for task in tasks]
    if len(ids) != len(set(ids)):
        raise ValueError("Task ids must be unique")
    return tasks


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True) + "\n")
