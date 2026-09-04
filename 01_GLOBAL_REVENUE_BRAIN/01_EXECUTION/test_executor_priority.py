import unittest

from autonomous_development_executor import queue_priority


class ExecutorPriorityTests(unittest.TestCase):
    def test_expected_hourly_return_has_priority(self):
        fast = {"risk_adjusted_hourly_value": "4", "estimated_payment_probability": "0.2", "decision_rank": "2"}
        large_but_slow = {"risk_adjusted_hourly_value": "0.5", "estimated_payment_probability": "0.8", "decision_rank": "1"}
        self.assertLess(queue_priority(fast), queue_priority(large_but_slow))

    def test_probability_breaks_hourly_tie(self):
        likely = {"risk_adjusted_hourly_value": "1", "estimated_payment_probability": "0.4", "decision_rank": "2"}
        unlikely = {"risk_adjusted_hourly_value": "1", "estimated_payment_probability": "0.1", "decision_rank": "1"}
        self.assertLess(queue_priority(likely), queue_priority(unlikely))


if __name__ == "__main__":
    unittest.main()
