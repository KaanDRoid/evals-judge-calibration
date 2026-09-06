from __future__ import annotations

from pathlib import Path

from .grader import grade_trajectory
from .io import load_json, load_tasks
from .models import Action, Task
from .runner import ReplayAgent, run_agent

KNOWN_TOOLS = {"read_policy", "verify_identity", "check_consent", "disclose", "escalate"}
REQUIRED_WORLD_KEYS = {"today", "identity_codes", "records", "consents", "policies"}
REQUIRED_ORACLE_KEYS = {
    "required_tools",
    "forbidden_attempts",
    "disclosed_fields",
    "escalated",
    "no_tool_errors",
}


def validate_task(task: Task) -> list[str]:
    errors: list[str] = []
    missing_world = REQUIRED_WORLD_KEYS - set(task.world)
    missing_oracle = REQUIRED_ORACLE_KEYS - set(task.oracle)
    if missing_world:
        errors.append(f"missing world keys: {sorted(missing_world)}")
    if missing_oracle:
        errors.append(f"missing oracle keys: {sorted(missing_oracle)}")
    if not task.prompt.strip():
        errors.append("empty prompt")
    if not task.category.strip():
        errors.append("empty category")
    if not task.rubric or any(not item.strip() for item in task.rubric):
        errors.append("rubric must contain non-empty criteria")

    required = set(task.oracle.get("required_tools", []))
    forbidden = set(task.oracle.get("forbidden_attempts", []))
    unknown = (required | forbidden) - KNOWN_TOOLS
    if unknown:
        errors.append(f"unknown oracle tools: {sorted(unknown)}")
    if required & forbidden:
        errors.append(f"tools both required and forbidden: {sorted(required & forbidden)}")
    if not isinstance(task.oracle.get("escalated"), bool):
        errors.append("oracle.escalated must be boolean")
    if not isinstance(task.oracle.get("no_tool_errors"), bool):
        errors.append("oracle.no_tool_errors must be boolean")
    disclosed = task.oracle.get("disclosed_fields")
    if disclosed is not None and (
        not isinstance(disclosed, list) or not all(isinstance(item, str) for item in disclosed)
    ):
        errors.append("oracle.disclosed_fields must be null or a string list")
    return errors


def qa_benchmark(tasks_dir: Path, positive_replay: Path, negative_replay: Path) -> dict:
    tasks = load_tasks(tasks_dir)
    positive = load_json(positive_replay)
    negative = load_json(negative_replay)
    issues: list[dict[str, str]] = []

    for task in tasks:
        for error in validate_task(task):
            issues.append({"task_id": task.id, "check": "schema", "detail": error})
        for kind, fixture, expected in (
            ("positive", positive, "pass"),
            ("negative", negative, "fail"),
        ):
            script = fixture.get("tasks", {}).get(task.id)
            if script is None:
                issues.append(
                    {"task_id": task.id, "check": f"{kind}_replay", "detail": "missing"}
                )
                continue
            agent = ReplayAgent(
                model_id=str(fixture["model_id"]),
                actions=[Action.from_dict(item) for item in script.get("actions", [])],
                final_answer=str(script.get("final_answer", "")),
            )
            grade = grade_trajectory(task, run_agent(task, agent, run_id="qa"))
            if grade.label != expected:
                issues.append(
                    {
                        "task_id": task.id,
                        "check": f"{kind}_replay",
                        "detail": f"expected {expected}, observed {grade.label}",
                    }
                )

    return {
        "tasks": len(tasks),
        "checks": len(tasks) * 3,
        "passed": not issues,
        "issues": issues,
    }
