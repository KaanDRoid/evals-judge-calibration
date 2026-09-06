import json
import tempfile
import unittest
from pathlib import Path

from calibra_eval.cli import compare_judge


class CompareJudgeTests(unittest.TestCase):
    def test_comparison_pairs_by_run_identity_and_counts_invalid(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            grades = root / "grades.jsonl"
            predictions = root / "predictions.jsonl"
            output = root / "report.json"
            grade_rows = [
                {"task_id": "disclosure-001", "model_id": "m", "run_id": "1", "label": "pass"},
                {"task_id": "disclosure-002", "model_id": "m", "run_id": "1", "label": "fail"},
            ]
            prediction_rows = [
                {"task_id": "disclosure-001", "model_id": "m", "run_id": "1", "judge_label": "pass"},
                {"task_id": "disclosure-002", "model_id": "m", "run_id": "1", "judge_label": ""},
            ]
            grades.write_text("".join(json.dumps(row) + "\n" for row in grade_rows), encoding="utf-8")
            predictions.write_text(
                "".join(json.dumps(row) + "\n" for row in prediction_rows), encoding="utf-8"
            )
            report = compare_judge(Path("benchmark/tasks"), grades, predictions, output)
            self.assertEqual(report["n"], 1)
            self.assertEqual(report["invalid_judge_outputs"], 1)
            self.assertEqual(report["reference_source"], "programmatic_grader")


if __name__ == "__main__":
    unittest.main()
