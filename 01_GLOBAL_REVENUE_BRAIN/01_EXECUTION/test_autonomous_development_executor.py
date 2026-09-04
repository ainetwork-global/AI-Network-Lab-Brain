import os
import unittest
from unittest.mock import patch

from autonomous_development_executor import POLICY, safe_environment


class AutonomousDevelopmentExecutorTests(unittest.TestCase):
    def test_zero_money_budget_is_enforced_by_policy(self):
        self.assertEqual(POLICY["budgets"]["money_usd"], 0)

    def test_untrusted_process_environment_strips_secrets(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "do-not-leak", "GEMINI_API_KEY": "do-not-leak", "NORMAL_SETTING": "safe"}):
            environment = safe_environment()
        self.assertNotIn("GITHUB_TOKEN", environment)
        self.assertNotIn("GEMINI_API_KEY", environment)
        self.assertEqual(environment["NORMAL_SETTING"], "safe")

    def test_only_trusted_model_process_receives_model_key(self):
        with patch.dict(os.environ, {"GITHUB_TOKEN": "do-not-leak", "GEMINI_API_KEY": "model-only"}):
            environment = safe_environment(allow_model_key=True)
        self.assertEqual(environment["GEMINI_API_KEY"], "model-only")
        self.assertNotIn("GITHUB_TOKEN", environment)

    def test_external_actions_are_not_autonomous(self):
        autonomous = set(POLICY["autonomous_actions"])
        approval = set(POLICY["approval_required_actions"])
        self.assertTrue(autonomous.isdisjoint(approval))
        self.assertIn("submit_deliverable", approval)
        self.assertIn("active_security_testing", approval)


if __name__ == "__main__":
    unittest.main()
