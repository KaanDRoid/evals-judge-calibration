import unittest

from calibra_eval.variance import prevalence_paradox_example, variance_report, wilson_interval


class VarianceTests(unittest.TestCase):
    def test_wilson_interval_contains_observed_rate(self):
        interval = wilson_interval(7, 10)
        self.assertLess(interval["low"], 0.7)
        self.assertGreater(interval["high"], 0.7)

    def test_unstable_task_is_reported(self):
        rows = [
            {"task_id": "t1", "model_id": "m1", "run_id": "seed-1", "label": "pass"},
            {"task_id": "t1", "model_id": "m1", "run_id": "seed-2", "label": "fail"},
        ]
        report = variance_report(rows)
        self.assertEqual(report["unstable_model_task_pairs"], 1)
        self.assertEqual(report["models"][0]["pass_rate"], 0.5)

    def test_accuracy_can_hide_zero_minority_recall(self):
        example = prevalence_paradox_example()
        self.assertEqual(example["accuracy"], 0.9)
        self.assertEqual(example["balanced_accuracy"], 0.5)
        self.assertEqual(example["cohen_kappa"], 0.0)
        self.assertEqual(example["pass_recall"], 0.0)


if __name__ == "__main__":
    unittest.main()
