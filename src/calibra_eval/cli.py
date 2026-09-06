from __future__ import annotations

import argparse
from pathlib import Path

from .adjudication import annotation_agreement
from .annotation import make_annotation_batch
from .calibration import calibration_report
from .failure_analysis import classify_failures, prevalence
from .grader import grade_trajectory
from .io import load_json, load_jsonl, load_tasks, write_json, write_jsonl
from .metrics import bootstrap_interval, classification_metrics
from .models import Action, Trajectory
from .ollama import (
    AGENT_PROMPT_VERSION,
    JUDGE_PROMPT_VERSION,
    OllamaAgent,
    OllamaClient,
    OllamaJudge,
)
from .qa import qa_benchmark
from .reporting import render_summary_charts
from .runner import ReplayAgent, run_agent
from .variance import variance_report


def run_replays(tasks_dir: Path, replay_paths: list[Path], output_dir: Path) -> dict:
    tasks = load_tasks(tasks_dir)
    trajectories = []
    grades = []
    failure_lists = []

    for replay_path in replay_paths:
        replay = load_json(replay_path)
        model_id = str(replay["model_id"])
        for task in tasks:
            script = replay["tasks"].get(task.id)
            if script is None:
                raise ValueError(f"{replay_path} has no replay for task {task.id}")
            agent = ReplayAgent(
                model_id=model_id,
                actions=[Action.from_dict(item) for item in script.get("actions", [])],
                final_answer=str(script.get("final_answer", "")),
            )
            trajectory = run_agent(task, agent, run_id="replay-001")
            grade = grade_trajectory(task, trajectory)
            trajectories.append(trajectory)
            grades.append(grade)
            failure_lists.append(classify_failures(trajectory, grade))

    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "trajectories.jsonl", (item.to_dict() for item in trajectories))
    write_jsonl(output_dir / "grades.jsonl", (item.to_dict() for item in grades))
    summary = {
        "artifact_type": "synthetic_replay_smoke_test",
        "trajectories": len(trajectories),
        "passed": sum(grade.label == "pass" for grade in grades),
        "failed": sum(grade.label == "fail" for grade in grades),
        "pass_rate": sum(grade.label == "pass" for grade in grades) / len(grades),
        "failure_prevalence": prevalence(failure_lists),
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def run_ollama(
    tasks_dir: Path,
    model: str,
    output_dir: Path,
    base_url: str,
    limit: int | None = None,
    max_steps: int = 8,
    runs_per_task: int = 1,
    start_seed: int = 7,
    temperature: float = 0.0,
) -> dict:
    tasks = load_tasks(tasks_dir)
    if limit is not None:
        if limit < 1:
            raise ValueError("limit must be positive")
        tasks = tasks[:limit]
    if runs_per_task < 1:
        raise ValueError("runs_per_task must be positive")
    if temperature < 0:
        raise ValueError("temperature cannot be negative")
    trajectories, grades, failure_lists = [], [], []
    try:
        for run_index in range(runs_per_task):
            seed = start_seed + run_index
            for task in tasks:
                agent = OllamaAgent(
                    model=model,
                    base_url=base_url,
                    seed=seed,
                    temperature=temperature,
                )
                trajectory = run_agent(
                    task, agent, run_id=f"seed-{seed}", max_steps=max_steps
                )
                grade = grade_trajectory(task, trajectory)
                trajectories.append(trajectory)
                grades.append(grade)
                failure_lists.append(classify_failures(trajectory, grade))
    finally:
        OllamaClient(model=model, base_url=base_url).unload()
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "trajectories.jsonl", (item.to_dict() for item in trajectories))
    write_jsonl(output_dir / "grades.jsonl", (item.to_dict() for item in grades))
    summary = {
        "artifact_type": "ollama_agent_run",
        "model": model,
        "agent_prompt_version": AGENT_PROMPT_VERSION,
        "resource_profile": {
            "context_length": 4096,
            "max_output_tokens": 256,
            "max_steps": max_steps,
            "runs_per_task": runs_per_task,
            "start_seed": start_seed,
            "temperature": temperature,
            "parallel_requests": 1,
            "unload_after_run": True,
        },
        "trajectories": len(trajectories),
        "passed": sum(grade.label == "pass" for grade in grades),
        "failed": sum(grade.label == "fail" for grade in grades),
        "pass_rate": sum(grade.label == "pass" for grade in grades) / len(grades),
        "failure_prevalence": prevalence(failure_lists),
    }
    write_json(output_dir / "summary.json", summary)
    return summary


def judge_ollama(
    tasks_dir: Path, trajectory_path: Path, model: str, output_path: Path, base_url: str
) -> list[dict]:
    tasks = {task.id: task for task in load_tasks(tasks_dir)}
    judge = OllamaJudge(model=model, base_url=base_url)
    predictions = []
    try:
        for index, row in enumerate(load_jsonl(trajectory_path), start=1):
            trajectory = Trajectory.from_dict(row)
            if trajectory.task_id not in tasks:
                raise ValueError(f"Unknown task id in trajectory: {trajectory.task_id}")
            prediction = {
                "decision_id": f"judge-{index:05d}",
                "task_id": trajectory.task_id,
                "category": tasks[trajectory.task_id].category,
                "model_id": trajectory.model_id,
                "run_id": trajectory.run_id,
                "judge_model": model,
                "judge_prompt_version": JUDGE_PROMPT_VERSION,
            }
            try:
                decision = judge.judge(tasks[trajectory.task_id], trajectory)
                prediction.update(
                    {
                        "judge_label": decision["label"],
                        "rationale": str(decision.get("rationale", "")),
                        "failure_mode": str(decision.get("failure_mode", "")),
                        "criteria": decision.get("criteria", []),
                        "judge_error": "",
                    }
                )
            except (ValueError, KeyError) as exc:
                prediction.update(
                    {
                        "judge_label": "",
                        "rationale": "",
                        "failure_mode": "invalid_judge_output",
                        "criteria": [],
                        "judge_error": str(exc),
                    }
                )
            predictions.append(prediction)
    finally:
        OllamaClient(model=model, base_url=base_url).unload()
    write_jsonl(output_path, predictions)
    return predictions


def compare_judge(
    tasks_dir: Path, grades_path: Path, predictions_path: Path, output_path: Path
) -> dict:
    tasks = {task.id: task for task in load_tasks(tasks_dir)}
    grades = {
        (row["task_id"], row["model_id"], row["run_id"]): row
        for row in load_jsonl(grades_path)
    }
    predictions = load_jsonl(predictions_path)
    paired = []
    invalid_judge_outputs = 0
    for prediction in predictions:
        key = (prediction["task_id"], prediction["model_id"], prediction["run_id"])
        if key not in grades:
            raise ValueError(f"Judge prediction has no matching grade: {key}")
        if prediction.get("judge_label") not in {"pass", "fail"}:
            invalid_judge_outputs += 1
            continue
        paired.append(
            {
                "task_id": prediction["task_id"],
                "category": tasks[prediction["task_id"]].category,
                "reference_label": grades[key]["label"],
                "judge_label": prediction["judge_label"],
            }
        )
    if not paired:
        raise ValueError("No valid judge predictions could be paired")
    reference = [row["reference_label"] for row in paired]
    predicted = [row["judge_label"] for row in paired]
    report = classification_metrics(reference, predicted)
    report["kappa_bootstrap_95"] = bootstrap_interval(reference, predicted)
    report["invalid_judge_outputs"] = invalid_judge_outputs
    report["reference_source"] = "programmatic_grader"
    report["interpretation_limit"] = (
        "This measures agreement with executable oracles, not human judgment."
    )
    drift_zones = []
    for category in sorted({row["category"] for row in paired}):
        group = [row for row in paired if row["category"] == category]
        agreement = sum(row["reference_label"] == row["judge_label"] for row in group) / len(group)
        drift_zones.append({"category": category, "n": len(group), "agreement": agreement})
    report["drift_zones"] = sorted(
        drift_zones, key=lambda item: (item["agreement"], item["category"])
    )
    write_json(output_path, report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="calibra-eval")
    subparsers = parser.add_subparsers(dest="command", required=True)

    demo = subparsers.add_parser("demo", help="Run the offline replay smoke suite")
    demo.add_argument("--tasks", type=Path, default=Path("benchmark/tasks"))
    demo.add_argument(
        "--replays",
        type=Path,
        nargs="+",
        default=[
            Path("examples/replays/scripted_cautious.json"),
            Path("examples/replays/scripted_buggy.json"),
        ],
    )
    demo.add_argument("--labels", type=Path, default=Path("data/demo_calibration.csv"))
    demo.add_argument("--output", type=Path, default=Path("artifacts/demo"))

    replay = subparsers.add_parser(
        "run-replays", help="Execute deterministic replay controls without calibration fixtures"
    )
    replay.add_argument("--tasks", type=Path, required=True)
    replay.add_argument("--replays", type=Path, nargs="+", required=True)
    replay.add_argument("--output", type=Path, required=True)

    calibrate = subparsers.add_parser("calibrate", help="Measure judge/reference agreement")
    calibrate.add_argument("labels", type=Path)
    calibrate.add_argument("--output", type=Path, default=Path("artifacts/calibration.json"))

    ollama = subparsers.add_parser("run-ollama", help="Run tasks with a local Ollama model")
    ollama.add_argument("--model", required=True)
    ollama.add_argument("--base-url", default="http://127.0.0.1:11434")
    ollama.add_argument("--tasks", type=Path, default=Path("benchmark/tasks"))
    ollama.add_argument("--output", type=Path, default=Path("artifacts/ollama"))
    ollama.add_argument("--limit", type=int, help="Run only the first N tasks")
    ollama.add_argument("--max-steps", type=int, default=8)
    ollama.add_argument("--runs-per-task", type=int, default=1)
    ollama.add_argument("--start-seed", type=int, default=7)
    ollama.add_argument("--temperature", type=float, default=0.0)

    judge = subparsers.add_parser("judge-ollama", help="Judge saved trajectories with Ollama")
    judge.add_argument("--model", required=True)
    judge.add_argument("--trajectories", type=Path, required=True)
    judge.add_argument("--base-url", default="http://127.0.0.1:11434")
    judge.add_argument("--tasks", type=Path, default=Path("benchmark/tasks"))
    judge.add_argument("--output", type=Path, default=Path("artifacts/judge_predictions.jsonl"))

    compare = subparsers.add_parser(
        "compare-judge", help="Compare judge predictions with programmatic grades"
    )
    compare.add_argument("--tasks", type=Path, required=True)
    compare.add_argument("--grades", type=Path, required=True)
    compare.add_argument("--predictions", type=Path, required=True)
    compare.add_argument("--output", type=Path, required=True)

    annotate = subparsers.add_parser(
        "make-annotation-batch", help="Create a blinded, shuffled human-labeling sheet"
    )
    annotate.add_argument("--tasks", type=Path, nargs="+", required=True)
    annotate.add_argument("--trajectories", type=Path, nargs="+", required=True)
    annotate.add_argument("--grades", type=Path, nargs="+")
    annotate.add_argument("--output", type=Path, required=True)
    annotate.add_argument("--key", type=Path, required=True)
    annotate.add_argument("--seed", type=int, default=17)
    annotate.add_argument("--sample-size", type=int)

    qa = subparsers.add_parser("qa-benchmark", help="Validate task schemas and replay controls")
    qa.add_argument("--tasks", type=Path, required=True)
    qa.add_argument("--positive-replay", type=Path, required=True)
    qa.add_argument("--negative-replay", type=Path, required=True)
    qa.add_argument("--output", type=Path, required=True)

    variance = subparsers.add_parser(
        "variance", help="Report repeated-run pass rates, uncertainty and unstable tasks"
    )
    variance.add_argument("--grades", type=Path, nargs="+", required=True)
    variance.add_argument("--output", type=Path, required=True)

    agreement = subparsers.add_parser(
        "annotation-agreement", help="Measure two blinded annotators before adjudication"
    )
    agreement.add_argument("--annotator-a", type=Path, required=True)
    agreement.add_argument("--annotator-b", type=Path, required=True)
    agreement.add_argument("--output", type=Path, required=True)
    agreement.add_argument("--disagreements", type=Path, required=True)

    charts = subparsers.add_parser(
        "render-charts", help="Render dependency-free SVGs from saved eval reports"
    )
    charts.add_argument("--judge-reports", type=Path, nargs="+", required=True)
    charts.add_argument("--agent-summaries", type=Path, nargs="+", required=True)
    charts.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "demo":
        summary = run_replays(args.tasks, args.replays, args.output)
        calibration = calibration_report(args.labels)
        write_json(args.output / "calibration.json", calibration)
        print(f"Replay pass rate: {summary['passed']}/{summary['trajectories']}")
        print(f"Demo judge kappa: {calibration['cohen_kappa']:.3f}")
        print(f"Artifacts: {args.output.resolve()}")
        return 0
    if args.command == "calibrate":
        report = calibration_report(args.labels)
        write_json(args.output, report)
        print(f"Kappa: {report['cohen_kappa']:.3f}; n={report['n']}")
        return 0
    if args.command == "run-replays":
        summary = run_replays(args.tasks, args.replays, args.output)
        print(
            f"Replay pass rate: {summary['passed']}/{summary['trajectories']}; "
            f"artifacts={args.output.resolve()}"
        )
        return 0
    if args.command == "run-ollama":
        summary = run_ollama(
            args.tasks,
            args.model,
            args.output,
            args.base_url,
            limit=args.limit,
            max_steps=args.max_steps,
            runs_per_task=args.runs_per_task,
            start_seed=args.start_seed,
            temperature=args.temperature,
        )
        print(f"Pass rate: {summary['passed']}/{summary['trajectories']}")
        return 0
    if args.command == "judge-ollama":
        predictions = judge_ollama(
            args.tasks, args.trajectories, args.model, args.output, args.base_url
        )
        print(f"Wrote {len(predictions)} judge decisions to {args.output.resolve()}")
        return 0
    if args.command == "compare-judge":
        report = compare_judge(args.tasks, args.grades, args.predictions, args.output)
        print(
            f"Agreement: {report['accuracy']:.3f}; kappa={report['cohen_kappa']:.3f}; "
            f"paired_n={report['n']}; invalid={report['invalid_judge_outputs']}"
        )
        return 0
    if args.command == "make-annotation-batch":
        summary = make_annotation_batch(
            args.tasks,
            args.trajectories,
            args.output,
            args.key,
            seed=args.seed,
            sample_size=args.sample_size,
            grades_path=args.grades,
        )
        print(
            f"Wrote {summary['decisions']} blinded decisions to {args.output.resolve()}; "
            f"keep {args.key.resolve()} hidden until labels are frozen"
        )
        return 0
    if args.command == "qa-benchmark":
        report = qa_benchmark(args.tasks, args.positive_replay, args.negative_replay)
        write_json(args.output, report)
        print(f"QA passed={report['passed']}; tasks={report['tasks']}; issues={len(report['issues'])}")
        return 0 if report["passed"] else 1
    if args.command == "variance":
        grades = [row for path in args.grades for row in load_jsonl(path)]
        report = variance_report(grades)
        write_json(args.output, report)
        print(
            f"Repeated grades={report['n']}; models={len(report['models'])}; "
            f"unstable pairs={report['unstable_model_task_pairs']}"
        )
        return 0
    if args.command == "annotation-agreement":
        report = annotation_agreement(
            args.annotator_a, args.annotator_b, args.output, args.disagreements
        )
        print(
            f"Human-human agreement={report['accuracy']:.3f}; "
            f"kappa={report['cohen_kappa']:.3f}; disagreements={report['disagreements']}"
        )
        return 0
    if args.command == "render-charts":
        summary = render_summary_charts(args.judge_reports, args.agent_summaries, args.output)
        print(
            f"Rendered judge rows={summary['judge_rows']} and "
            f"failure rows={summary['failure_rows']} to {args.output.resolve()}"
        )
        return 0
    raise AssertionError("unreachable")


if __name__ == "__main__":
    raise SystemExit(main())
