import unittest
from pathlib import Path

from calibra_eval.failure_analysis import classify_failures
from calibra_eval.grader import grade_trajectory
from calibra_eval.io import load_json, load_tasks
from calibra_eval.models import Action
from calibra_eval.runner import ReplayAgent, run_agent


class GraderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = {task.id: task for task in load_tasks(Path("benchmark/tasks"))}

    def _run_fixture(self, fixture_name: str, task_id: str):
        fixture = load_json(Path("examples/replays") / fixture_name)
        script = fixture["tasks"][task_id]
        agent = ReplayAgent(
            fixture["model_id"],
            [Action.from_dict(action) for action in script["actions"]],
            script["final_answer"],
        )
        trajectory = run_agent(self.tasks[task_id], agent, "test")
        return trajectory, grade_trajectory(self.tasks[task_id], trajectory)

    def test_cautious_fixture_passes(self):
        for task_id in self.tasks:
            with self.subTest(task_id=task_id):
                _, grade = self._run_fixture("scripted_cautious.json", task_id)
                self.assertEqual(grade.label, "pass")

    def test_buggy_fixture_fails_seeded_defects(self):
        expected_failures = set(self.tasks) - {"disclosure-002"}
        for task_id in expected_failures:
            with self.subTest(task_id=task_id):
                _, grade = self._run_fixture("scripted_buggy.json", task_id)
                self.assertEqual(grade.label, "fail")

    def test_forbidden_attempt_fails_even_when_environment_blocks_it(self):
        _, grade = self._run_fixture("scripted_buggy.json", "disclosure-003")
        criterion = next(item for item in grade.criteria if item.name == "forbidden_attempt:disclose")
        self.assertFalse(criterion.passed)

    def test_hallucinated_tool_in_final_text_is_classified(self):
        trajectory, grade = self._run_fixture("scripted_buggy.json", "disclosure-008")
        trajectory.final_answer = '{"name":"invented_lookup","parameters":{}}'
        self.assertIn("hallucinated_tool", classify_failures(trajectory, grade))


if __name__ == "__main__":
    unittest.main()
