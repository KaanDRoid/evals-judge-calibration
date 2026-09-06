from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

Label = Literal["pass", "fail"]


@dataclass(frozen=True)
class Action:
    tool: str
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Action:
        arguments = value.get("arguments", {})
        if not isinstance(arguments, dict):
            raise ValueError("action.arguments must be a JSON object")  # noqa: TRY004
        return cls(tool=str(value["tool"]), arguments=dict(arguments))


@dataclass(frozen=True)
class Task:
    id: str
    category: str
    prompt: str
    world: dict[str, Any]
    oracle: dict[str, Any]
    rubric: list[str]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Task:
        return cls(
            id=str(value["id"]),
            category=str(value["category"]),
            prompt=str(value["prompt"]),
            world=dict(value["world"]),
            oracle=dict(value["oracle"]),
            rubric=list(value.get("rubric", [])),
        )


@dataclass
class Event:
    tool: str
    arguments: dict[str, Any]
    result: dict[str, Any]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Event:
        return cls(
            tool=str(value["tool"]),
            arguments=dict(value.get("arguments", {})),
            result=dict(value.get("result", {})),
        )


@dataclass
class Trajectory:
    task_id: str
    model_id: str
    run_id: str
    actions: list[Action]
    events: list[Event]
    final_answer: str
    final_state: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> Trajectory:
        return cls(
            task_id=str(value["task_id"]),
            model_id=str(value["model_id"]),
            run_id=str(value["run_id"]),
            actions=[Action.from_dict(item) for item in value.get("actions", [])],
            events=[Event.from_dict(item) for item in value.get("events", [])],
            final_answer=str(value.get("final_answer", "")),
            final_state=dict(value.get("final_state", {})),
        )


@dataclass(frozen=True)
class CriterionResult:
    name: str
    passed: bool
    detail: str


@dataclass
class Grade:
    task_id: str
    model_id: str
    run_id: str
    label: Label
    criteria: list[CriterionResult]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
