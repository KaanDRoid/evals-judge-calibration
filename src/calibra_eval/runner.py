from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .environment import ComplianceEnvironment
from .models import Action, Task, Trajectory


class AgentOutputError(ValueError):
    """The agent responded, but its response did not match the action protocol."""


@dataclass(frozen=True)
class AgentTurn:
    action: Action | None = None
    final_answer: str | None = None


class Agent(Protocol):
    model_id: str

    def next_turn(
        self, task: Task, environment: ComplianceEnvironment, history: list[dict]
    ) -> AgentTurn: ...


class ReplayAgent:
    def __init__(self, model_id: str, actions: list[Action], final_answer: str):
        self.model_id = model_id
        self._actions = actions
        self._final_answer = final_answer
        self._index = 0

    def next_turn(
        self, task: Task, environment: ComplianceEnvironment, history: list[dict]
    ) -> AgentTurn:
        del task, environment, history
        if self._index < len(self._actions):
            action = self._actions[self._index]
            self._index += 1
            return AgentTurn(action=action)
        return AgentTurn(final_answer=self._final_answer)


def run_agent(task: Task, agent: Agent, run_id: str, max_steps: int = 12) -> Trajectory:
    environment = ComplianceEnvironment(task)
    actions: list[Action] = []
    events = []
    history: list[dict] = []
    final_answer = ""
    agent_errors: list[str] = []

    for _ in range(max_steps):
        try:
            turn = agent.next_turn(task, environment, history)
        except AgentOutputError as exc:
            agent_errors.append(str(exc))
            final_answer = "Agent output did not match the required protocol."
            break
        if turn.final_answer is not None:
            final_answer = turn.final_answer
            break
        if turn.action is None:
            final_answer = "Agent returned neither an action nor a final answer."
            break
        actions.append(turn.action)
        event = environment.step(turn.action)
        events.append(event)
        history.append({"action": turn.action, "result": event.result})
    else:
        final_answer = "Step limit exceeded."

    final_state = environment.snapshot()
    final_state["agent_errors"] = agent_errors
    return Trajectory(
        task_id=task.id,
        model_id=agent.model_id,
        run_id=run_id,
        actions=actions,
        events=events,
        final_answer=final_answer,
        final_state=final_state,
    )
