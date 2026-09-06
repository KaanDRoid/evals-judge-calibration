import unittest
from pathlib import Path

from calibra_eval.calibration import calibration_report
from calibra_eval.metrics import classification_metrics, cohen_kappa


class MetricTests(unittest.TestCase):
    def test_perfect_agreement(self):
        reference = ["pass", "fail", "pass", "fail"]
        report = classification_metrics(reference, reference)
        self.assertEqual(report["accuracy"], 1.0)
        self.assertEqual(report["cohen_kappa"], 1.0)
        self.assertEqual(report["matthews_correlation"], 1.0)

    def test_known_kappa(self):
        reference = ["pass", "pass", "fail", "fail"]
        predicted = ["pass", "fail", "fail", "fail"]
        self.assertAlmostEqual(cohen_kappa(reference, predicted), 0.5)

    def test_demo_calibration_exposes_drift(self):
        report = calibration_report(Path("data/demo_calibration.csv"))
        self.assertEqual(report["n"], 24)
        self.assertEqual(report["reference_sources"], ["synthetic_fixture"])
        self.assertEqual(report["drift_zones"][0]["category"], "adversarial")
        self.assertLess(report["drift_zones"][0]["agreement"], 0.6)


if __name__ == "__main__":
    unittest.main()

