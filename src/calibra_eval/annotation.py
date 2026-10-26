from __future__ import annotations

import csv
import hashlib
import json
import random
from pathlib import Path

from .io import load_jsonl, load_tasks, write_jsonl
from .models import Task, Trajectory

ANNOTATION_FIELDS = [
    "decision_id",
    "category",
    "request",
    "rubric_json",
    "events_json",
    "final_answer",
    "terminal_state_json",
    "annotator_id",
    "label",
    "confidence",
    "uncertainty_reason",
    "failure_mode",
    "rationale",
]


def _compact_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _decision_id(trajectory: Trajectory, seed: int) -> str:
    raw = f"{seed}\0{trajectory.task_id}\0{trajectory.model_id}\0{trajectory.run_id}"
    return f"ann-{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]}"


def _paths(value: Path | list[Path]) -> list[Path]:
    return value if isinstance(value, list) else [value]


def _stratified_sample(
    trajectories: list[Trajectory],
    tasks: dict[str, Task],
    grade_labels: dict[tuple[str, str, str], str],
    sample_size: int,
    rng: random.Random,
) -> list[Trajectory]:
    groups: dict[tuple[str, str, str], list[Trajectory]] = {}
    for trajectory in trajectories:
        identity = (trajectory.task_id, trajectory.model_id, trajectory.run_id)
        if identity not in grade_labels:
            raise ValueError(f"No grade supplied for trajectory: {identity}")
        stratum = (tasks[trajectory.task_id].category, trajectory.model_id, grade_labels[identity])
        groups.setdefault(stratum, []).append(trajectory)
    for group in groups.values():
        rng.shuffle(group)
    selected: list[Trajectory] = []
    active = sorted(groups)
    while active and len(selected) < sample_size:
        next_active = []
        for stratum in active:
            if len(selected) >= sample_size:
                break
            group = groups[stratum]
            if group:
                selected.append(group.pop())
            if group:
                next_active.append(stratum)
        active = next_active
    rng.shuffle(selected)
    return selected


def make_annotation_batch(
    tasks_dir: Path | list[Path],
    trajectories_path: Path | list[Path],
    output_csv: Path,
    key_path: Path,
    *,
    seed: int = 17,
    sample_size: int | None = None,
    grades_path: Path | list[Path] | None = None,
) -> dict[str, int]:
    """Create a blinded annotation sheet and a separate identity key.

    The sheet intentionally omits task ids, model ids, run ids, private worlds,
    executable oracles, and programmatic grades. The key must not be given to
    annotators before labels are frozen.
    """

    tasks: dict[str, Task] = {}
    for directory in _paths(tasks_dir):
        for task in load_tasks(directory):
            if task.id in tasks:
                raise ValueError(f"Duplicate task id across directories: {task.id}")
            tasks[task.id] = task
    trajectories = [
        Trajectory.from_dict(row)
        for path in _paths(trajectories_path)
        for row in load_jsonl(path)
    ]
    if not trajectories:
        raise ValueError("No trajectories found")
    if sample_size is not None and sample_size < 1:
        raise ValueError("sample_size must be positive")

    unknown = sorted({item.task_id for item in trajectories} - set(tasks))
    if unknown:
        raise ValueError(f"Unknown task ids in trajectories: {', '.join(unknown)}")

    rng = random.Random(seed)
    rng.shuffle(trajectories)
    grade_labels: dict[tuple[str, str, str], str] = {}
    if grades_path is not None:
        for path in _paths(grades_path):
            for row in load_jsonl(path):
                identity = (str(row["task_id"]), str(row["model_id"]), str(row["run_id"]))
                if identity in grade_labels:
                    raise ValueError(f"Duplicate grade identity: {identity}")
                grade_labels[identity] = str(row["label"])
    if sample_size is not None and sample_size < len(trajectories):
        trajectories = (
            _stratified_sample(trajectories, tasks, grade_labels, sample_size, rng)
            if grade_labels
            else trajectories[:sample_size]
        )

    seen_ids: set[str] = set()
    sheet_rows: list[dict[str, str]] = []
    key_rows: list[dict[str, str]] = []
    for trajectory in trajectories:
        task = tasks[trajectory.task_id]
        decision_id = _decision_id(trajectory, seed)
        if decision_id in seen_ids:
            raise ValueError(
                "Duplicate trajectory identity; task_id, model_id and run_id must be unique"
            )
        seen_ids.add(decision_id)
        sheet_rows.append(
            {
                "decision_id": decision_id,
                "category": task.category,
                "request": task.prompt,
                "rubric_json": _compact_json(task.rubric),
                "events_json": _compact_json(
                    [
                        {
                            "event_id": index,
                            "tool": event.tool,
                            "arguments": event.arguments,
                            "result": event.result,
                        }
                        for index, event in enumerate(trajectory.events, start=1)
                    ]
                ),
                "final_answer": trajectory.final_answer,
                "terminal_state_json": _compact_json(trajectory.final_state),
                "annotator_id": "",
                "label": "",
                "confidence": "",
                "uncertainty_reason": "",
                "failure_mode": "",
                "rationale": "",
            }
        )
        key_rows.append(
            {
                "decision_id": decision_id,
                "task_id": trajectory.task_id,
                "model_id": trajectory.model_id,
                "run_id": trajectory.run_id,
            }
        )

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=ANNOTATION_FIELDS)
        writer.writeheader()
        writer.writerows(sheet_rows)
    write_jsonl(key_path, key_rows)
    summary = {"decisions": len(sheet_rows), "seed": seed}
    if grade_labels:
        labels = [
            grade_labels[(item.task_id, item.model_id, item.run_id)] for item in trajectories
        ]
        summary["reference_pass"] = labels.count("pass")
        summary["reference_fail"] = labels.count("fail")
    return summary
