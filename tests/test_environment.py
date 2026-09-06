import unittest

from calibra_eval.environment import ComplianceEnvironment
from calibra_eval.io import load_tasks
from calibra_eval.models import Action


class EnvironmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tasks = {task.id: task for task in load_tasks(__import__("pathlib").Path("benchmark/tasks"))}

    def test_authorized_disclosure_changes_state(self):
        environment = ComplianceEnvironment(self.tasks["disclosure-002"])
        environment.step(Action("verify_identity", {"party_id": "A-7", "verification_code": "adviser-7"}))
        environment.step(Action("check_consent", {"subject_id": "C-200", "requester_id": "A-7"}))
        event = environment.step(
            Action("disclose", {"subject_id": "C-200", "requester_id": "A-7", "fields": ["account_balance"]})
        )
        self.assertTrue(event.result["ok"])
        self.assertEqual(environment.snapshot()["disclosures"][0]["fields"], ["account_balance"])

    def test_unsafe_disclosure_is_blocked_and_audited(self):
        environment = ComplianceEnvironment(self.tasks["disclosure-003"])
        event = environment.step(
            Action("disclose", {"subject_id": "C-300", "requester_id": "A-9", "fields": ["transactions"]})
        )
        self.assertFalse(event.result["ok"])
        self.assertEqual(environment.snapshot()["disclosures"], [])
        self.assertEqual(environment.snapshot()["tool_errors"][0]["reason"], "requester_not_verified")

    def test_expired_consent_is_invalid(self):
        environment = ComplianceEnvironment(self.tasks["disclosure-004"])
        event = environment.step(Action("check_consent", {"subject_id": "C-400", "requester_id": "A-8"}))
        self.assertFalse(event.result["valid"])

    def test_disclosure_rejects_string_instead_of_field_list(self):
        environment = ComplianceEnvironment(self.tasks["disclosure-001"])
        environment.step(Action("verify_identity", {"party_id": "C-100", "verification_code": "alpha-100"}))
        event = environment.step(
            Action("disclose", {"subject_id": "C-100", "requester_id": "C-100", "fields": "account_balance"})
        )
        self.assertFalse(event.result["ok"])
        self.assertEqual(event.result["error"], "fields_must_be_a_non_empty_string_list")

    def test_revoked_consent_is_invalid(self):
        task = load_tasks(__import__("pathlib").Path("benchmark/holdout_tasks"))[2]
        environment = ComplianceEnvironment(task)
        event = environment.step(
            Action("check_consent", {"subject_id": "C-930", "requester_id": "A-31"})
        )
        self.assertFalse(event.result["valid"])
        self.assertTrue(event.result["revoked"])


if __name__ == "__main__":
    unittest.main()
