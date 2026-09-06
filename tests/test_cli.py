import tempfile
import unittest
from pathlib import Path

from calibra_eval.cli import run_replays


class CliTests(unittest.TestCase):
    def test_replay_run_writes_auditable_artifacts(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            summary = run_replays(
                Path("benchmark/tasks"),
                [
                    Path("examples/replays/scripted_cautious.json"),
                    Path("examples/replays/scripted_buggy.json"),
                ],
                output,
            )
            self.assertEqual(summary["trajectories"], 16)
            self.assertEqual(summary["passed"], 8)
            self.assertEqual(summary["failed"], 8)
            self.assertTrue((output / "trajectories.jsonl").exists())
            self.assertTrue((output / "grades.jsonl").exists())
            self.assertTrue((output / "summary.json").exists())

    def test_holdout_fixture_is_balanced(self):
        with tempfile.TemporaryDirectory() as directory:
            summary = run_replays(
                Path("benchmark/holdout_tasks"),
                [
                    Path("examples/holdout_replays/reference_positive.json"),
                    Path("examples/holdout_replays/seeded_defects.json"),
                ],
                Path(directory),
            )
            self.assertEqual(summary["trajectories"], 8)
            self.assertEqual(summary["passed"], 4)
            self.assertEqual(summary["failed"], 4)


if __name__ == "__main__":
    unittest.main()
