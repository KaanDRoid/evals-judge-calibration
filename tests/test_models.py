import unittest

from calibra_eval.models import Action, Event, Trajectory


class ModelSerializationTests(unittest.TestCase):
    def test_trajectory_round_trip(self):
        original = Trajectory(
            task_id="task",
            model_id="model",
            run_id="run",
            actions=[Action("read_policy", {"topic": "disclosure"})],
            events=[Event("read_policy", {"topic": "disclosure"}, {"ok": True})],
            final_answer="done",
            final_state={"disclosures": []},
        )
        restored = Trajectory.from_dict(original.to_dict())
        self.assertEqual(restored, original)

    def test_action_rejects_non_object_arguments(self):
        with self.assertRaisesRegex(ValueError, "JSON object"):
            Action.from_dict({"tool": "read_policy", "arguments": ["disclosure"]})


if __name__ == "__main__":
    unittest.main()
