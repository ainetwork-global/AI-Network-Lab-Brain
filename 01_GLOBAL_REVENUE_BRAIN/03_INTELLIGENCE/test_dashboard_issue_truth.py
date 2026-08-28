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
    def test_output_fields_include_official_enrichment_columns(self):
        fields = truth.output_fieldnames(
            [{"title": "Candidate", "eligibility_status": "eligible"}]
        )
        self.assertIn("eligibility_status", fields)
        self.assertEqual(len(fields), len(set(fields)))

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

    def test_high_competition_is_blocked_and_live_terms_replace_inferences(self):
        issue = {
            "state": "open",
            "locked": False,
            "comments": 59,
            "title": "[ Bounty $3k ] Research proposals",
            "body": (
                "$3,000 USD for an accepted submission. "
                "Payment details will be handled privately after acceptance."
            ),
            "labels": [{"name": "bounty"}],
            "updated_at": "2026-08-20T01:17:55Z",
            "assignee": None,
        }
        comments = [{"body": "/attempt"}]
        pulls = [
            {"number": number, "title": f"Research packet #{5}", "body": "Closes #5"}
            for number in range(6, 9)
        ]
        original_api = truth.api
        try:
            truth.api = lambda path: (
                issue if path.endswith("/issues/5")
                else comments if "/comments?" in path
                else pulls
            )
            row = {
                "url": "https://github.com/alexzzz430/Cognitive-OS/issues/5",
                "payment_method": "GitHub Sponsors",
                "kyc_required": "0",
            }
            status, reason, _, count = truth.classify(row)
        finally:
            truth.api = original_api

        self.assertEqual(status, "BLOCKED_HIGH_COMPETITION")
        self.assertIn("3 PRs concorrentes", reason)
        self.assertEqual(count, 59)
        self.assertEqual(row["_open_competing_prs"], "3")
        self.assertEqual(row["reward_basis"], "accepted_submission_not_guaranteed")
        self.assertEqual(row["payment_method"], "private_after_acceptance")
        self.assertEqual(row["kyc_required"], "unknown_not_disclosed")

    def test_competing_pr_reference_regex_matches_issue_number(self):
        original_api = truth.api
        try:
            truth.api = lambda _: [
                {"number": 47, "title": "Research packet", "body": "Closes #5"}
            ]
            matches = truth.competing_pull_requests(
                "alexzzz430", "Cognitive-OS", "5", "Research proposals"
            )
        finally:
            truth.api = original_api
        self.assertEqual(matches, [47])

    def test_bug_bounty_selection_gets_security_review_path(self):
        self.assertEqual(
            intake.execution_path("AUTHORIZED_BUG_BOUNTY_REVIEW_REQUIRED"),
            "validate_scope_then_run_local_security_review",
        )


if __name__ == "__main__":
    unittest.main()
