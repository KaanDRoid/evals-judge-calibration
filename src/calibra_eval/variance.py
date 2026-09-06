from __future__ import annotations

import math
from collections import defaultdict

from .metrics import classification_metrics


def wilson_interval(successes: int, n: int, z: float = 1.959963984540054) -> dict[str, float]:
    if n < 1 or successes < 0 or successes > n:
        raise ValueError("successes and n must satisfy 0 <= successes <= n and n >= 1")
    p = successes / n
    denominator = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denominator
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denominator
    return {"low": max(0.0, center - half), "high": min(1.0, center + half)}


def prevalence_paradox_example() -> dict:
    reference = ["fail"] * 90 + ["pass"] * 10
    predicted = ["fail"] * 100
    result = classification_metrics(reference, predicted)
    return {
        "description": "A majority-class judge on a 90/10 reference split",
        "accuracy": result["accuracy"],
        "balanced_accuracy": result["balanced_accuracy"],
        "cohen_kappa": result["cohen_kappa"],
        "pass_recall": result["per_class"]["pass"]["recall"],
    }


def variance_report(grades: list[dict]) -> dict:
    if not grades:
        raise ValueError("No grades supplied")
    by_model: dict[str, list[dict]] = defaultdict(list)
    by_model_task: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in grades:
        if row.get("label") not in {"pass", "fail"}:
            raise ValueError(f"Unsupported grade label: {row.get('label')}")
        by_model[str(row["model_id"])].append(row)
        by_model_task[(str(row["model_id"]), str(row["task_id"]))].append(row)

    models = []
    for model_id, rows in sorted(by_model.items()):
        passes = sum(row["label"] == "pass" for row in rows)
        models.append(
            {
                "model_id": model_id,
                "n": len(rows),
                "tasks": len({row["task_id"] for row in rows}),
                "runs": len({row["run_id"] for row in rows}),
                "passes": passes,
                "pass_rate": passes / len(rows),
                "pass_rate_wilson_95": wilson_interval(passes, len(rows)),
            }
        )

    task_runs = []
    for (model_id, task_id), rows in sorted(by_model_task.items()):
        passes = sum(row["label"] == "pass" for row in rows)
        rate = passes / len(rows)
        task_runs.append(
            {
                "model_id": model_id,
                "task_id": task_id,
                "n": len(rows),
                "pass_rate": rate,
                "outcome_variance": rate * (1 - rate),
                "unstable": 0 < passes < len(rows),
            }
        )
    return {
        "n": len(grades),
        "models": models,
        "task_runs": task_runs,
        "unstable_model_task_pairs": sum(row["unstable"] for row in task_runs),
        "accuracy_vs_kappa_demo": prevalence_paradox_example(),
    }
