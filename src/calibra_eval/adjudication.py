from __future__ import annotations

import csv
from pathlib import Path

from .io import write_json
from .metrics import bootstrap_interval, classification_metrics


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
        if row["label"] not in {"pass", "fail"}:
            raise ValueError(f"Decision {decision_id} has no valid frozen label")
        if not row["annotator_id"].strip():
            raise ValueError(f"Decision {decision_id} has no annotator_id")
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
    labels_a = [first[item]["label"] for item in ids]
    labels_b = [second[item]["label"] for item in ids]
    report = classification_metrics(labels_a, labels_b)
    report["kappa_bootstrap_95"] = bootstrap_interval(labels_a, labels_b)
    report["annotator_a"] = sorted({first[item]["annotator_id"] for item in ids})
    report["annotator_b"] = sorted({second[item]["annotator_id"] for item in ids})
    disagreements = []
    for decision_id in ids:
        left, right = first[decision_id], second[decision_id]
        if left["label"] != right["label"] or left["failure_mode"] != right["failure_mode"]:
            disagreements.append(
                {
                    "decision_id": decision_id,
                    "annotator_a_label": left["label"],
                    "annotator_b_label": right["label"],
                    "annotator_a_failure_mode": left["failure_mode"],
                    "annotator_b_failure_mode": right["failure_mode"],
                    "adjudicated_label": "",
                    "adjudicated_failure_mode": "",
                    "adjudicator_id": "",
                    "adjudication_rationale": "",
                }
            )
    report["disagreements"] = len(disagreements)
    report["disagreement_rate"] = len(disagreements) / len(ids)
    write_json(report_path, report)
    disagreement_path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(disagreements[0]) if disagreements else [
        "decision_id",
        "annotator_a_label",
        "annotator_b_label",
        "annotator_a_failure_mode",
        "annotator_b_failure_mode",
        "adjudicated_label",
        "adjudicated_failure_mode",
        "adjudicator_id",
        "adjudication_rationale",
    ]
    with disagreement_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(disagreements)
    return report
