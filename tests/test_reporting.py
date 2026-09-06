import json
import tempfile
import unittest
from pathlib import Path

from calibra_eval.reporting import render_summary_charts


class ReportingTests(unittest.TestCase):
    def test_renders_standalone_svg_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            judge = root / "judge.json"
            agent = root / "agent.json"
            judge.write_text(
                json.dumps({"n": 7, "invalid_judge_outputs": 1, "accuracy": 0.75}),
                encoding="utf-8",
            )
            agent.write_text(
                json.dumps(
                    {
                        "model": "small:1b",
                        "failure_prevalence": {
                            "missing_check": {"share_of_failed_trajectories": 0.5}
                        },
                    }
                ),
                encoding="utf-8",
            )
            output = root / "charts"
            render_summary_charts([judge], [agent], output)
            self.assertIn("<svg", (output / "judge-quality.svg").read_text(encoding="utf-8"))
            self.assertIn("50.0%", (output / "failures.svg").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
