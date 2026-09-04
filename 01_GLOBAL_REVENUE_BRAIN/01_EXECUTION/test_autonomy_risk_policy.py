import unittest

from autonomy_risk_policy import assess


class AutonomyRiskPolicyTests(unittest.TestCase):
    def test_verified_internal_work_is_green(self):
        decision = assess({"title": "Implement parser", "eligibility_status": "confirmed eligible"})
        self.assertEqual(decision.level, "GREEN")
        self.assertEqual(decision.decision, "AUTONOMOUS_INTERNAL_EXECUTION")

    def test_public_submission_requires_approval(self):
        decision = assess({"requirements": "Submit a pull request"}, action="external_submission")
        self.assertEqual(decision.level, "YELLOW")
        self.assertEqual(decision.decision, "HUMAN_APPROVAL_REQUIRED")

    def test_submission_text_does_not_block_internal_development(self):
        decision = assess({"requirements": "Submit a pull request", "eligibility_status": "confirmed eligible"})
        self.assertEqual(decision.decision, "AUTONOMOUS_INTERNAL_EXECUTION")

    def test_upfront_payment_is_red(self):
        decision = assess({"requirements": "Registration fee of USD 5"})
        self.assertEqual(decision.level, "RED")
        self.assertEqual(decision.decision, "HUMAN_APPROVAL_REQUIRED")

    def test_fake_account_is_always_rejected(self):
        decision = assess({"requirements": "Create a fake account"})
        self.assertEqual(decision.level, "PROHIBITED")
        self.assertEqual(decision.decision, "REJECT")

    def test_unknown_material_fact_requires_approval(self):
        decision = assess({"payment_status": "not confirmed"})
        self.assertEqual(decision.decision, "HUMAN_APPROVAL_REQUIRED")


if __name__ == "__main__":
    unittest.main()
