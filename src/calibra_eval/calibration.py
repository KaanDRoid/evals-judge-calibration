from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from .metrics import bootstrap_interval, classification_metrics

REQUIRED_COLUMNS = {
    "decision_id",
    "task_id",
    "category",
    "model_id",
    "reference_label",
    "judge_label",
    "reference_source",
}


def calibration_report(path: Path) -> dict:
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Calibration file is empty")
    missing = REQUIRED_COLUMNS - set(rows[0])
    if missing:
        raise ValueError(f"Calibration file is missing columns: {sorted(missing)}")

    reference = [row["reference_label"] for row in rows]
    predicted = [row["judge_label"] for row in rows]
    report = classification_metrics(reference, predicted)
    report["kappa_bootstrap_95"] = bootstrap_interval(reference, predicted)
    report["reference_sources"] = sorted({row["reference_source"] for row in rows})

    grouped: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    drift_zones = []
    for category, group in grouped.items():
        agreements = [row["reference_label"] == row["judge_label"] for row in group]
        drift_zones.append(
            {"category": category, "n": len(group), "agreement": sum(agreements) / len(group)}
        )
    report["drift_zones"] = sorted(drift_zones, key=lambda item: (item["agreement"], item["category"]))
    return report

