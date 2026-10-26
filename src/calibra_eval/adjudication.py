from __future__ import annotations

import csv
from pathlib import Path

from .io import write_json
from .metrics import bootstrap_interval, classification_metrics

QUEUE_FIELDS = [
    "decision_id",
    "review_reason",
    "annotator_a_label",
    "annotator_b_label",
    "annotator_a_failure_mode",
    "annotator_b_failure_mode",
    "annotator_a_confidence",
    "annotator_b_confidence",
    "annotator_a_uncertainty_reason",
    "annotator_b_uncertainty_reason",
    "annotator_a_rationale",
    "annotator_b_rationale",
    "adjudicated_label",
    "adjudicated_failure_mode",
    "adjudicator_id",
    "adjudication_rationale",
]


def _read_annotations(path: Path) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Annotation file is empty: {path}")
    required = {"decision_id", "annotator_id", "label", "failure_mode", "rationale"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Annotation file is missing columns: {sorted(missing)}")
    result = {}
    for row in rows:
        decision_id = row["decision_id"].strip()
        if not decision_id or decision_id in result:
            raise ValueError(f"Missing or duplicate decision_id in {path}: {decision_id!r}")
        if row["label"] not in {"pass", "fail", "uncertain"}:
            raise ValueError(f"Decision {decision_id} has no valid frozen label")
        if not row["annotator_id"].strip():
            raise ValueError(f"Decision {decision_id} has no annotator_id")
        confidence = row.get("confidence", "")
        if confidence not in {"", "1", "2", "3", "4", "5"}:
            raise ValueError(f"Decision {decision_id} confidence must be an integer from 1 to 5")
        if row["label"] == "uncertain" and not (row.get("uncertainty_reason") or "").strip():
            raise ValueError(f"Decision {decision_id} requires uncertainty_reason")
        result[decision_id] = row
    return result


def annotation_agreement(
    first_path: Path,
    second_path: Path,
    report_path: Path,
    disagreement_path: Path,
) -> dict:
    first = _read_annotations(first_path)
    second = _read_annotations(second_path)
    if set(first) != set(second):
        raise ValueError("Annotator files must contain identical decision_id sets")
    ids = sorted(first)
    binary_ids = [
        item
        for item in ids
        if first[item]["label"] != "uncertain" and second[item]["label"] != "uncertain"
    ]
    labels_a = [first[item]["label"] for item in binary_ids]
    labels_b = [second[item]["label"] for item in binary_ids]
    if binary_ids:
        report = classification_metrics(labels_a, labels_b)
        report["kappa_bootstrap_95"] = bootstrap_interval(labels_a, labels_b)
        report["kappa_status"] = "computed"
        if len(set(labels_a + labels_b)) == 1:
            report["cohen_kappa"] = None
            report["kappa_bootstrap_95"] = None
            report["kappa_status"] = "undefined_single_class"
    else:
        report = dict.fromkeys(
            [
                "accuracy",
                "balanced_accuracy",
                "cohen_kappa",
                "matthews_correlation",
                "confusion",
                "per_class",
                "prevalence",
                "kappa_bootstrap_95",
            ]
        )
        report["n"] = 0
        report["kappa_status"] = "no_binary_pairs"
    report["total_decisions"] = len(ids)
    report["binary_pair_coverage"] = len(binary_ids) / len(ids)
    report["uncertain_a"] = sum(first[item]["label"] == "uncertain" for item in ids)
    report["uncertain_b"] = sum(second[item]["label"] == "uncertain" for item in ids)
    report["metrics_scope"] = "paired_binary_labels_only"
    report["annotator_a"] = sorted({first[item]["annotator_id"] for item in ids})
    report["annotator_b"] = sorted({second[item]["annotator_id"] for item in ids})
    queue = []
    disagreements = 0
    for decision_id in ids:
        left, right = first[decision_id], second[decision_id]
        differs = left["label"] != right["label"] or left["failure_mode"] != right["failure_mode"]
        uncertain = "uncertain" in {left["label"], right["label"]}
        disagreements += int(differs)
        if differs or uncertain:
            row = dict.fromkeys(QUEUE_FIELDS, "")
            row["decision_id"] = decision_id
            row["review_reason"] = "uncertainty" if uncertain else "disagreement"
            for side, source in [("a", left), ("b", right)]:
                for field in [
                    "label",
                    "failure_mode",
                    "confidence",
                    "uncertainty_reason",
                    "rationale",
                ]:
                    row[f"annotator_{side}_{field}"] = source.get(field, "")
            queue.append(row)
    report["disagreements"] = disagreements
    report["disagreement_rate"] = disagreements / len(ids)
    report["adjudication_required"] = len(queue)
    write_json(report_path, report)
    disagreement_path.parent.mkdir(parents=True, exist_ok=True)
    with disagreement_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=QUEUE_FIELDS)
        writer.writeheader()
        writer.writerows(queue)
    return report
