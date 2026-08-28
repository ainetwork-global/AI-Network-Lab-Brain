from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


truth = load("github_candidate_truth_gate")
intake = load("dashboard_selection_intake")


class DashboardIssueTruthTests(unittest.TestCase):
    def test_official_maximum_replaces_unlabelled_vault_amount(self):
        url = "https://immunefi.com/bug-bounty/hedera/information/"
        candidate = {
            "url": url,
            "reward_amount": "14500.0",
            "reward_currency": "USD",
        }
        official = {
            url: {
                "reward_amount": "30000.0",
                "reward_currency": "USD",
                "kyc_required": "1",
            }
        }

        result = truth.apply_official_truth(candidate, official)

        self.assertEqual(result["reward_amount"], "30000.0")
        self.assertEqual(result["reward_basis"], "maximum_advertised_reward")
        self.assertEqual(result["kyc_required"], "1")
        self.assertEqual(result["source_validation"], "official_adapter")

    def test_immunefi_is_not_rejected_for_not_being_a_github_issue(self):
        status, reason, live_state, comments = truth.classify(
            {
                "url": "https://immunefi.com/bug-bounty/hedera/information/",
                "source": "Immunefi",
                "category": "authorized_bug_bounty",
                "kyc_required": "1",
            }
        )

        self.assertEqual(status, "AUTHORIZED_BUG_BOUNTY_REVIEW_REQUIRED")
        self.assertIn("KYC", reason)
        self.assertEqual(live_state, "official_program")
        self.assertEqual(comments, 0)

    def test_bug_bounty_selection_gets_security_review_path(self):
        self.assertEqual(
            intake.execution_path("AUTHORIZED_BUG_BOUNTY_REVIEW_REQUIRED"),
            "validate_scope_then_run_local_security_review",
        )


if __name__ == "__main__":
    unittest.main()
