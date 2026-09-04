import unittest

from microtask_fast_lane import evaluate


class FastLaneTests(unittest.TestCase):
    def test_blocks_archived_candidate(self):
        self.assertIsNone(evaluate({"decision_route": "ARCHIVE_BLOCKED", "reward_amount": "10"}, {}))

    def test_rejects_zero_reward(self):
        self.assertIsNone(evaluate({"decision_route": "HUMAN_DECISION_REQUIRED", "reward_amount": "0"}, {}))

    def test_small_quick_task_can_beat_slow_large_task(self):
        quick = evaluate({"decision_route": "AUTONOMOUS_TECHNICAL_EXECUTION", "reward_amount": "2", "estimated_hours": "0.25", "estimated_payment_probability": "0.5", "automation_eligible": "true"}, {})
        slow = evaluate({"decision_route": "AUTONOMOUS_TECHNICAL_EXECUTION", "reward_amount": "50", "estimated_hours": "100", "estimated_payment_probability": "0.5", "automation_eligible": "true"}, {})
        self.assertIsNone(slow)
        self.assertEqual(quick["fast_lane_route"], "AUTO_PREPARE")

    def test_maximum_bug_bounty_prize_is_not_fast_cashflow(self):
        result = evaluate({"decision_route": "HUMAN_DECISION_REQUIRED", "reward_amount": "500000", "estimated_hours": "4", "estimated_payment_probability": "0.1", "category": "authorized_bug_bounty", "reward_basis": "maximum_advertised_reward"}, {})
        self.assertIsNone(result)

    def test_history_adjusts_probability_without_overriding_live_evidence(self):
        row = {"decision_route": "HUMAN_DECISION_REQUIRED", "reward_amount": "5", "estimated_hours": "1", "estimated_payment_probability": "0.2", "source": "known"}
        result = evaluate(row, {"known": (8, 0, 20.0)})
        self.assertGreater(float(result["learned_payment_probability"]), 0.2)
        self.assertEqual(result["fast_lane_route"], "REQUEST_APPROVAL")


if __name__ == "__main__":
    unittest.main()
