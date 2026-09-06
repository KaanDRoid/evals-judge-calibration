import csv
import tempfile
import unittest
from pathlib import Path

from calibra_eval.adjudication import annotation_agreement

FIELDS = ["decision_id", "annotator_id", "label", "failure_mode", "rationale"]


def _write(path: Path, annotator: str, labels: list[str]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        for index, label in enumerate(labels, start=1):
            writer.writerow(
                {
                    "decision_id": f"d-{index}",
                    "annotator_id": annotator,
                    "label": label,
                    "failure_mode": "none" if label == "pass" else "missing_required_check",
                    "rationale": "reviewed",
                }
            )


class AnnotationAgreementTests(unittest.TestCase):
    def test_reports_disagreement_and_writes_queue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            left, right = root / "a.csv", root / "b.csv"
            _write(left, "reviewer-a", ["pass", "fail", "pass", "fail"])
            _write(right, "reviewer-b", ["pass", "fail", "fail", "fail"])
            report_path, queue_path = root / "report.json", root / "queue.csv"
            report = annotation_agreement(left, right, report_path, queue_path)
            self.assertEqual(report["disagreements"], 1)
            self.assertEqual(report["accuracy"], 0.75)
            self.assertTrue(report_path.exists())
            with queue_path.open(encoding="utf-8", newline="") as handle:
                queue = list(csv.DictReader(handle))
            self.assertEqual(queue[0]["decision_id"], "d-3")
            self.assertEqual(queue[0]["adjudicated_label"], "")


if __name__ == "__main__":
    unittest.main()
