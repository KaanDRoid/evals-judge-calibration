import unittest
from pathlib import Path

from calibra_eval.io import load_tasks
from calibra_eval.models import Trajectory
from calibra_eval.ollama import OllamaJudge


class JudgeValidationTests(unittest.TestCase):
    def test_fail_cannot_use_none_failure_mode(self):
        task = load_tasks(Path("benchmark/tasks"))[0]
        judge = OllamaJudge("fake")
        judge.client.chat = lambda *args, **kwargs: (
            '{"criteria":['
            '{"passed":false,"evidence_event_ids":[],"rationale":"missing"},'
            '{"passed":true,"evidence_event_ids":[],"rationale":"ok"},'
            '{"passed":true,"evidence_event_ids":[],"rationale":"ok"}'
            '],"failure_mode":"none"}'
        )
        trajectory = Trajectory(task.id, "model", "run", [], [], "answer", {})
        with self.assertRaisesRegex(ValueError, "must identify"):
            judge.judge(task, trajectory)

    def test_overall_label_is_aggregated_from_criteria(self):
        task = load_tasks(Path("benchmark/tasks"))[0]
        judge = OllamaJudge("fake")
        judge.client.chat = lambda *args, **kwargs: (
            '{"criteria":['
            '{"passed":true,"evidence_event_ids":[],"rationale":"ok"},'
            '{"passed":true,"evidence_event_ids":[],"rationale":"ok"},'
            '{"passed":true,"evidence_event_ids":[],"rationale":"ok"}'
            '],"failure_mode":"none"}'
        )
        trajectory = Trajectory(task.id, "model", "run", [], [], "answer", {})
        decision = judge.judge(task, trajectory)
        self.assertEqual(decision["label"], "pass")
        self.assertEqual(len(decision["criteria"]), 3)


if __name__ == "__main__":
    unittest.main()
