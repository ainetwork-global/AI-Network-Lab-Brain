import csv
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_handoff_queue() -> None:
    script = Path(__file__).with_name("human_login_handoff_engine.py")
    subprocess.run([sys.executable, str(script)], check=True)
    output = ROOT / "04_OPPORTUNITIES" / "HUMAN_LOGIN_HANDOFF_QUEUE.csv"
    with output.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert any(row["handoff_status"] == "LOGIN_REQUIRED_TO_DISCOVER" for row in rows)
    assert all(row["initial_cost_allowed"] == "false" for row in rows)
    assert all(row["external_submission_allowed"] == "false" for row in rows)
    assert all(row["identity_action_owner"] == "account_holder" for row in rows)


if __name__ == "__main__":
    test_handoff_queue()
    print("human login handoff tests: ok")
