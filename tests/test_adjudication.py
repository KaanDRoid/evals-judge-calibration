import csv
import tempfile
import unittest
from pathlib import Path

import pytest

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


def test_uncertainty_is_queued_even_when_both_annotators_abstain(tmp_path):
    fields = FIELDS + ["confidence", "uncertainty_reason"]
    for name, labels in [
        ("a", ["pass", "fail", "uncertain", "uncertain"]),
        ("b", ["pass", "fail", "pass", "uncertain"]),
    ]:
        with (tmp_path / f"{name}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for index, label in enumerate(labels):
                writer.writerow(
                    {
                        "decision_id": f"d-{index}",
                        "annotator_id": name,
                        "label": label,
                        "failure_mode": "none",
                        "rationale": f"evidence-{name}-{index}",
                        "confidence": "2" if label == "uncertain" else "5",
                        "uncertainty_reason": "scope ambiguity" if label == "uncertain" else "",
                    }
                )
    report = annotation_agreement(
        tmp_path / "a.csv", tmp_path / "b.csv", tmp_path / "report.json", tmp_path / "queue.csv"
    )
    assert report["total_decisions"] == 4
    assert report["n"] == 2
    assert report["binary_pair_coverage"] == 0.5
    assert report["uncertain_a"] == 2
    assert report["uncertain_b"] == 1
    assert report["accuracy"] == 1.0
    assert report["disagreements"] == 1
    assert report["adjudication_required"] == 2
    with (tmp_path / "queue.csv").open(encoding="utf-8", newline="") as handle:
        queue = list(csv.DictReader(handle))
    assert [row["decision_id"] for row in queue] == ["d-2", "d-3"]
    assert queue[1]["review_reason"] == "uncertainty"
    assert queue[1]["annotator_a_confidence"] == "2"
    assert queue[1]["annotator_a_uncertainty_reason"] == "scope ambiguity"
    assert queue[1]["annotator_b_rationale"] == "evidence-b-3"


def test_all_uncertain_has_no_binary_metrics(tmp_path):
    for name in ["a", "b"]:
        with (tmp_path / f"{name}.csv").open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=FIELDS + ["uncertainty_reason"])
            writer.writeheader()
            writer.writerow(
                {
                    "decision_id": "d-1",
                    "annotator_id": name,
                    "label": "uncertain",
                    "failure_mode": "",
                    "rationale": "review",
                    "uncertainty_reason": "insufficient evidence",
                }
            )
    report = annotation_agreement(
        tmp_path / "a.csv", tmp_path / "b.csv", tmp_path / "report.json", tmp_path / "queue.csv"
    )
    assert report["n"] == 0
    assert report["binary_pair_coverage"] == 0
    assert report["accuracy"] is None
    assert report["cohen_kappa"] is None
    assert report["kappa_bootstrap_95"] is None
    assert report["confusion"] is None
    assert report["adjudication_required"] == 1


@pytest.mark.parametrize("confidence", ["0", "6", "2.5", "high", "01"])
def test_rejects_invalid_confidence(tmp_path, confidence):
    for name in ["a", "b"]:
        _write(tmp_path / f"{name}.csv", name, ["pass", "fail"])
    path = tmp_path / "a.csv"
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["confidence"] = confidence
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS + ["confidence"])
        writer.writeheader()
        writer.writerows(rows)
    with pytest.raises(ValueError, match="confidence"):
        annotation_agreement(path, tmp_path / "b.csv", tmp_path / "r.json", tmp_path / "q.csv")


def test_uncertain_requires_reason(tmp_path):
    _write(tmp_path / "a.csv", "a", ["uncertain"])
    _write(tmp_path / "b.csv", "b", ["pass"])
    with pytest.raises(ValueError, match="uncertainty_reason"):
        annotation_agreement(
            tmp_path / "a.csv", tmp_path / "b.csv", tmp_path / "r.json", tmp_path / "q.csv"
        )


def test_single_class_identical_labels_have_undefined_kappa(tmp_path):
    for name in ["a", "b"]:
        _write(tmp_path / f"{name}.csv", name, ["pass", "pass"])
    report = annotation_agreement(
        tmp_path / "a.csv", tmp_path / "b.csv", tmp_path / "r.json", tmp_path / "q.csv"
    )
    assert report["accuracy"] == 1
    assert report["cohen_kappa"] is None
    assert report["kappa_bootstrap_95"] is None
    assert report["kappa_status"] == "undefined_single_class"


if __name__ == "__main__":
    unittest.main()
