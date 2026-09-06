import unittest
from pathlib import Path

from calibra_eval.qa import qa_benchmark


class BenchmarkQATests(unittest.TestCase):
    def test_development_tasks_pass_qa_controls(self):
        report = qa_benchmark(
            Path("benchmark/tasks"),
            Path("examples/replays/scripted_cautious.json"),
            Path("examples/replays/scripted_buggy.json"),
        )
        self.assertTrue(report["passed"], report["issues"])
        self.assertEqual(report["tasks"], 8)


if __name__ == "__main__":
    unittest.main()
