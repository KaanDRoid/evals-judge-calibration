import csv
import json
import tempfile
import unittest
from pathlib import Path

import pytest

from calibra_eval.cli import main, run_replays


class CliTests(unittest.TestCase):
    def test_replay_run_writes_auditable_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            summary = run_replays(
                Path("benchmark/tasks"),
                [
                    Path("examples/replays/scripted_cautious.json"),
                    Path("examples/replays/scripted_buggy.json"),
                ],
                output,
            )
            self.assertEqual(summary["trajectories"], 16)
            self.assertEqual(summary["passed"], 8)
            self.assertEqual(summary["failed"], 8)
            self.assertTrue((output / "trajectories.jsonl").exists())
            self.assertTrue((output / "grades.jsonl").exists())
            self.assertTrue((output / "summary.json").exists())

    def test_holdout_fixture_is_balanced(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = run_replays(
                Path("benchmark/holdout_tasks"),
                [
                    Path("examples/holdout_replays/reference_positive.json"),
                    Path("examples/holdout_replays/seeded_defects.json"),
                ],
                Path(directory),
            )
            self.assertEqual(summary["trajectories"], 8)
            self.assertEqual(summary["passed"], 4)
            self.assertEqual(summary["failed"], 4)


@pytest.mark.parametrize("label", ["uncertain", "pass"])
def test_annotation_cli_handles_undefined_metrics(tmp_path, capsys, label):
    for name in ["a", "b"]:
        with (tmp_path / f"{name}.csv").open("w", encoding="utf-8", newline="") as handle:
            fields = [
                "decision_id",
                "annotator_id",
                "label",
                "failure_mode",
                "rationale",
                "uncertainty_reason",
            ]
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            writer.writerow(
                {
                    "decision_id": "d-1",
                    "annotator_id": name,
                    "label": label,
                    "failure_mode": "",
                    "rationale": "review",
                    "uncertainty_reason": "not enough evidence" if label == "uncertain" else "",
                }
            )
    result = main(
        [
            "annotation-agreement",
            "--annotator-a",
            str(tmp_path / "a.csv"),
            "--annotator-b",
            str(tmp_path / "b.csv"),
            "--output",
            str(tmp_path / "report.json"),
            "--disagreements",
            str(tmp_path / "queue.csv"),
        ]
    )
    assert result == 0
    assert "kappa=undefined" in capsys.readouterr().out
    report = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))
    assert report["cohen_kappa"] is None


if __name__ == "__main__":
    unittest.main()
