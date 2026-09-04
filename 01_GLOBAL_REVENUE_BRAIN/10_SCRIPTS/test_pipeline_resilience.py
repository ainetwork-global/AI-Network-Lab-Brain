import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

import run_revenue_pipeline as pipeline


class PipelineResilienceTests(unittest.TestCase):
    def setUp(self):
        pipeline.RESULTS.clear()
        self.script = pipeline.PROJECT_ROOT / "02_DISCOVERY" / "global_revenue_hunter.py"

    @patch("run_revenue_pipeline.subprocess.run")
    def test_noncritical_source_failure_does_not_stop_cycle(self, mocked):
        mocked.return_value = subprocess.CompletedProcess([], 1, "", "offline")
        pipeline.run_step("source", self.script)
        self.assertEqual(pipeline.RESULTS[-1]["returncode"], 1)

    @patch("run_revenue_pipeline.subprocess.run")
    def test_critical_failure_stops_cycle(self, mocked):
        mocked.return_value = subprocess.CompletedProcess([], 1, "", "broken")
        with self.assertRaises(RuntimeError):
            pipeline.run_step("database", self.script, critical=True)

    @patch("run_revenue_pipeline.subprocess.run", side_effect=subprocess.TimeoutExpired(["python"], 1))
    def test_noncritical_timeout_does_not_stop_cycle(self, mocked):
        pipeline.run_step("slow source", self.script)
        self.assertEqual(pipeline.RESULTS[-1]["returncode"], -1)


if __name__ == "__main__":
    unittest.main()
