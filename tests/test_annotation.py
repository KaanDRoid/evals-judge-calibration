import csv
import json
from pathlib import Path

import pytest

from calibra_eval.annotation import ANNOTATION_FIELDS, make_annotation_batch


def _write_trajectory(path: Path) -> None:
    row = {
        "task_id": "holdout-001",
        "model_id": "secret-model",
        "run_id": "secret-run",
        "actions": [],
        "events": [
            {
                "tool": "verify_identity",
                "arguments": {"person_id": "customer-201"},
                "result": {"verified": True},
            }
        ],
        "final_answer": "Completed.",
        "final_state": {"verified": True},
    }
    path.write_text(json.dumps(row) + "\n", encoding="utf-8")


def test_annotation_batch_is_blinded_and_reproducible(tmp_path: Path) -> None:
    trajectories = tmp_path / "trajectories.jsonl"
    _write_trajectory(trajectories)
    sheet = tmp_path / "batch.csv"
    key = tmp_path / "key.jsonl"

    summary = make_annotation_batch(
        Path("benchmark/holdout_tasks"), trajectories, sheet, key, seed=23
    )

    assert summary == {"decisions": 1, "seed": 23}
    with sheet.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert list(rows[0]) == ANNOTATION_FIELDS
    assert rows[0]["label"] == ""
    assert rows[0]["confidence"] == ""
    assert rows[0]["uncertainty_reason"] == ""
    assert "secret-model" not in sheet.read_text(encoding="utf-8")
    assert "secret-run" not in sheet.read_text(encoding="utf-8")
    assert "oracle" not in sheet.read_text(encoding="utf-8").lower()

    key_row = json.loads(key.read_text(encoding="utf-8"))
    assert key_row["model_id"] == "secret-model"
    assert key_row["run_id"] == "secret-run"
    assert key_row["decision_id"] == rows[0]["decision_id"]

    second_sheet = tmp_path / "batch-2.csv"
    second_key = tmp_path / "key-2.jsonl"
    make_annotation_batch(
        Path("benchmark/holdout_tasks"), trajectories, second_sheet, second_key, seed=23
    )
    assert second_sheet.read_bytes() == sheet.read_bytes()
    assert second_key.read_bytes() == key.read_bytes()


def test_annotation_batch_rejects_nonpositive_sample_size(tmp_path: Path) -> None:
    trajectories = tmp_path / "trajectories.jsonl"
    _write_trajectory(trajectories)
    with pytest.raises(ValueError, match="positive"):
        make_annotation_batch(
            Path("benchmark/holdout_tasks"),
            trajectories,
            tmp_path / "batch.csv",
            tmp_path / "key.jsonl",
            sample_size=0,
        )


def test_stratified_sample_retains_both_reference_classes(tmp_path: Path) -> None:
    trajectories = tmp_path / "trajectories.jsonl"
    grades = tmp_path / "grades.jsonl"
    trajectory_rows = []
    grade_rows = []
    for index, label in enumerate(["fail", "fail", "pass"], start=1):
        trajectory_rows.append(
            {
                "task_id": "holdout-001",
                "model_id": "model-a",
                "run_id": f"run-{index}",
                "actions": [],
                "events": [],
                "final_answer": "review me",
                "final_state": {},
            }
        )
        grade_rows.append(
            {
                "task_id": "holdout-001",
                "model_id": "model-a",
                "run_id": f"run-{index}",
                "label": label,
                "criteria": [],
            }
        )
    trajectories.write_text(
        "".join(json.dumps(row) + "\n" for row in trajectory_rows), encoding="utf-8"
    )
    grades.write_text("".join(json.dumps(row) + "\n" for row in grade_rows), encoding="utf-8")

    summary = make_annotation_batch(
        Path("benchmark/holdout_tasks"),
        trajectories,
        tmp_path / "batch.csv",
        tmp_path / "key.jsonl",
        sample_size=2,
        grades_path=grades,
    )

    assert summary["decisions"] == 2
    assert summary["reference_pass"] == 1
    assert summary["reference_fail"] == 1
