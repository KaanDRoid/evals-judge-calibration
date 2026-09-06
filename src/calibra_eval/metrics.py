from __future__ import annotations

import math
import random
from collections import Counter
from collections.abc import Callable, Sequence
from statistics import mean

LABELS = ("fail", "pass")


def confusion_counts(reference: Sequence[str], predicted: Sequence[str]) -> dict[str, int]:
    _validate(reference, predicted)
    counts = {f"{actual}_as_{guess}": 0 for actual in LABELS for guess in LABELS}
    for actual, guess in zip(reference, predicted, strict=True):
        counts[f"{actual}_as_{guess}"] += 1
    return counts


def classification_metrics(reference: Sequence[str], predicted: Sequence[str]) -> dict:
    _validate(reference, predicted)
    counts = confusion_counts(reference, predicted)
    per_class = {}
    recalls = []
    for label in LABELS:
        tp = counts[f"{label}_as_{label}"]
        fp = sum(counts[f"{other}_as_{label}"] for other in LABELS if other != label)
        fn = sum(counts[f"{label}_as_{other}"] for other in LABELS if other != label)
        precision = _safe_div(tp, tp + fp)
        recall = _safe_div(tp, tp + fn)
        f1 = _safe_div(2 * precision * recall, precision + recall)
        recalls.append(recall)
        per_class[label] = {"precision": precision, "recall": recall, "f1": f1, "support": tp + fn}

    accuracy = mean(actual == guess for actual, guess in zip(reference, predicted, strict=True))
    return {
        "n": len(reference),
        "accuracy": accuracy,
        "balanced_accuracy": mean(recalls),
        "cohen_kappa": cohen_kappa(reference, predicted),
        "matthews_correlation": matthews_correlation(reference, predicted),
        "confusion": counts,
        "per_class": per_class,
        "prevalence": {label: Counter(reference)[label] / len(reference) for label in LABELS},
    }


def cohen_kappa(reference: Sequence[str], predicted: Sequence[str]) -> float:
    _validate(reference, predicted)
    n = len(reference)
    observed = sum(a == b for a, b in zip(reference, predicted, strict=True)) / n
    ref_counts, pred_counts = Counter(reference), Counter(predicted)
    expected = sum((ref_counts[label] / n) * (pred_counts[label] / n) for label in LABELS)
    return _safe_div(observed - expected, 1 - expected)


def matthews_correlation(reference: Sequence[str], predicted: Sequence[str]) -> float:
    counts = confusion_counts(reference, predicted)
    tp = counts["pass_as_pass"]
    tn = counts["fail_as_fail"]
    fp = counts["fail_as_pass"]
    fn = counts["pass_as_fail"]
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return _safe_div(tp * tn - fp * fn, denominator)


def bootstrap_interval(
    reference: Sequence[str],
    predicted: Sequence[str],
    metric: Callable[[Sequence[str], Sequence[str]], float] = cohen_kappa,
    samples: int = 2_000,
    confidence: float = 0.95,
    seed: int = 7,
) -> dict[str, float | int]:
    _validate(reference, predicted)
    rng = random.Random(seed)
    estimates = []
    n = len(reference)
    for _ in range(samples):
        indices = [rng.randrange(n) for _ in range(n)]
        sampled_reference = [reference[index] for index in indices]
        sampled_predicted = [predicted[index] for index in indices]
        estimates.append(metric(sampled_reference, sampled_predicted))
    estimates.sort()
    tail = (1 - confidence) / 2
    low = estimates[int(tail * (samples - 1))]
    high = estimates[int((1 - tail) * (samples - 1))]
    return {"estimate": metric(reference, predicted), "low": low, "high": high, "samples": samples}


def _validate(reference: Sequence[str], predicted: Sequence[str]) -> None:
    if not reference or len(reference) != len(predicted):
        raise ValueError("Labels must be non-empty and have equal length")
    invalid = (set(reference) | set(predicted)) - set(LABELS)
    if invalid:
        raise ValueError(f"Unsupported labels: {sorted(invalid)}")


def _safe_div(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0

