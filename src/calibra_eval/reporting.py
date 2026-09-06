from __future__ import annotations

import html
from pathlib import Path

from .io import load_json


def _bar_svg(title: str, rows: list[tuple[str, float]], path: Path) -> None:
    width = 860
    row_height = 32
    height = 70 + row_height * len(rows)
    label_width = 330
    bar_width = 450
    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}">'
        ),
        '<rect width="100%" height="100%" fill="#0f172a"/>',
        (
            f'<text x="24" y="34" fill="#f8fafc" font-family="sans-serif" font-size="20">'
            f"{html.escape(title)}</text>"
        ),
    ]
    for index, (label, value) in enumerate(rows):
        y = 58 + index * row_height
        clamped = max(0.0, min(1.0, value))
        parts.extend(
            [
                (
                    f'<text x="24" y="{y + 17}" fill="#cbd5e1" font-family="monospace" '
                    f'font-size="13">{html.escape(label)}</text>'
                ),
                (
                    f'<rect x="{label_width}" y="{y}" width="{bar_width}" height="20" '
                    'rx="3" fill="#334155"/>'
                ),
                (
                    f'<rect x="{label_width}" y="{y}" width="{bar_width * clamped:.1f}" '
                    'height="20" rx="3" fill="#38bdf8"/>'
                ),
                (
                    f'<text x="{label_width + bar_width + 10}" y="{y + 16}" fill="#f8fafc" '
                    f'font-family="monospace" font-size="13">{value:.1%}</text>'
                ),
            ]
        )
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts) + "\n", encoding="utf-8")


def render_summary_charts(
    judge_reports: list[Path], agent_summaries: list[Path], output_dir: Path
) -> dict[str, int]:
    judge_rows: list[tuple[str, float]] = []
    for path in judge_reports:
        report = load_json(path)
        name = path.stem.replace("-report", "")
        valid = int(report["n"])
        invalid = int(report.get("invalid_judge_outputs", 0))
        judge_rows.append((f"{name} / valid accuracy", float(report["accuracy"])))
        judge_rows.append((f"{name} / output coverage", valid / (valid + invalid)))
    _bar_svg("Judge accuracy and output coverage", judge_rows, output_dir / "judge-quality.svg")

    failure_rows: list[tuple[str, float]] = []
    for path in agent_summaries:
        summary = load_json(path)
        model = str(summary["model"]).split(":")[0]
        for mode, values in summary["failure_prevalence"].items():
            failure_rows.append(
                (f"{model} / {mode}", float(values["share_of_failed_trajectories"]))
            )
    failure_rows.sort(key=lambda item: (-item[1], item[0]))
    _bar_svg("Failure prevalence among failed trajectories", failure_rows, output_dir / "failures.svg")
    return {"judge_rows": len(judge_rows), "failure_rows": len(failure_rows)}
