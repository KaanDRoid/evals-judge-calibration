import unittest
from pathlib import Path

from calibra_eval.grader import grade_trajectory
from calibra_eval.io import load_tasks
from calibra_eval.runner import AgentOutputError, run_agent


class BrokenAgent:
    model_id = "broken"

    def next_turn(self, task, environment, history):
        del task, environment, history
        raise AgentOutputError("bad JSON")


class RunnerTests(unittest.TestCase):
    def test_invalid_agent_output_is_preserved_and_graded(self):
        task = load_tasks(Path("benchmark/tasks"))[0]
        trajectory = run_agent(task, BrokenAgent(), "test")
        grade = grade_trajectory(task, trajectory)
        self.assertEqual(grade.label, "fail")
        self.assertEqual(trajectory.final_state["agent_errors"], ["bad JSON"])


if __name__ == "__main__":
    unittest.main()
