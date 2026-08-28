from __future__ import annotations

import csv
import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
TRUTH_QUEUE = ROOT / "04_OPPORTUNITIES" / "LIVE_TRUTH_EXECUTION_QUEUE.csv"
OFFICIAL_SOURCE_INPUT = ROOT / "04_OPPORTUNITIES" / "official_source_candidates.csv"
OFFICIAL_ELIGIBILITY_INPUT = ROOT / "04_OPPORTUNITIES" / "official_eligible_queue.csv"
SELECTION_QUEUE = ROOT / "04_OPPORTUNITIES" / "DASHBOARD_HUMAN_SELECTION_QUEUE.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_DASHBOARD_SELECTION.md"
ALLOWED_HOSTS = {
    "github.com", "algora.io", "immunefi.com", "www.immunefi.com",
    "devpost.com", "superteam.fun", "www.superteam.fun",
}
FIELDS = [
    "issue_number", "selected_at", "selected_by", "status", "truth_rank",
    "truth_status", "title", "source", "url", "reward_amount",
    "reward_currency", "reward_basis", "payment_method", "kyc_required",
    "truth_reason", "recommended_action", "execution_path",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def extract_url(body: str) -> str:
    match = re.search(r"(?im)^Opportunity URL:\s*(https://\S+)\s*$", body)
    return match.group(1).strip() if match else ""


def execution_path(status: str) -> str:
    if "BUG_BOUNTY" in status:
        return "validate_scope_then_run_local_security_review"
    if "SOURCE_REVIEW_REQUIRED" in status:
        return "validate_source_scope_eligibility_and_payment"
    if "CONFIRMATION_REQUIRED" in status:
        return "confirm_availability_and_competition_before_development"
    if "RETRY_REQUIRED" in status:
        return "retry_live_validation_then_reassess"
    return "prepare_individual_execution_plan"


def canonical_candidate(candidate: dict[str, str]) -> dict[str, str]:
    """Restore labelled official values when a later parser confused them."""
    result = dict(candidate)
    official = next(
        (
            row for row in read_csv(OFFICIAL_SOURCE_INPUT)
            if row.get("url") == candidate.get("url")
        ),
        None,
    )
    if official:
        try:
            reward = float(official.get("reward_amount") or 0)
        except ValueError:
            reward = 0
        if reward > 0:
            result["reward_amount"] = str(reward)
            result["reward_currency"] = official.get("reward_currency") or "USD"
            result["reward_basis"] = "maximum_advertised_reward"
    eligible = next(
        (
            row for row in read_csv(OFFICIAL_ELIGIBILITY_INPUT)
            if row.get("url") == candidate.get("url")
        ),
        None,
    )
    if eligible and eligible.get("kyc_required", "") != "":
        result["kyc_required"] = eligible["kyc_required"]
    return result


def main() -> int:
    event_path = Path(os.environ.get("GITHUB_EVENT_PATH", ""))
    if not event_path.is_file():
        raise SystemExit("GITHUB_EVENT_PATH is required")
    event = json.loads(event_path.read_text(encoding="utf-8"))
    issue = event.get("issue") or {}
    repository = event.get("repository") or {}
    actor = (event.get("sender") or {}).get("login", "")
    owner = (repository.get("owner") or {}).get("login", "")
    title = str(issue.get("title") or "")
    if actor != owner or not title.startswith(("[DASHBOARD REVIEW]", "[BRAIN ANALYSIS]")):
        raise SystemExit("Selection rejected: only the repository owner may request it")

    url = extract_url(str(issue.get("body") or ""))
    if urlparse(url).hostname not in ALLOWED_HOSTS:
        raise SystemExit("Selection rejected: unsupported opportunity URL")
    truth_rows = read_csv(TRUTH_QUEUE)
    candidate = next((row for row in truth_rows if row.get("url") == url), None)
    if not candidate:
        raise SystemExit("Selection rejected: URL is not in the live truth queue")
    candidate = canonical_candidate(candidate)
    status = candidate.get("truth_status", "")
    if status.startswith("BLOCKED_") or not re.search(
        r"REVIEW_REQUIRED|CONFIRMATION_REQUIRED|RETRY_REQUIRED", status
    ):
        raise SystemExit("Selection rejected: candidate is not in the human-review queue")

    issue_number = str(issue.get("number") or "")
    existing = read_csv(SELECTION_QUEUE)
    existing = [row for row in existing if row.get("issue_number") != issue_number]
    row: dict[str, Any] = {
        "issue_number": issue_number,
        "selected_at": datetime.now(timezone.utc).isoformat(),
        "selected_by": actor,
        "status": "USER_SELECTED_FOR_ANALYSIS",
        "truth_rank": candidate.get("truth_rank", ""),
        "truth_status": status,
        "title": candidate.get("title", ""),
        "source": candidate.get("source", ""),
        "url": url,
        "reward_amount": candidate.get("reward_amount", ""),
        "reward_currency": candidate.get("reward_currency", ""),
        "reward_basis": candidate.get("reward_basis", "reported_amount_unverified"),
        "payment_method": candidate.get("payment_method", ""),
        "kyc_required": candidate.get("kyc_required", ""),
        "truth_reason": candidate.get("truth_reason", ""),
        "recommended_action": candidate.get("recommended_action", ""),
        "execution_path": execution_path(status),
    }
    existing.append(row)
    SELECTION_QUEUE.parent.mkdir(parents=True, exist_ok=True)
    with SELECTION_QUEUE.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(existing)

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        "# Latest Dashboard Selection\n\n"
        f"- GitHub request: `#{issue_number}`\n"
        f"- Selected by: `{actor}`\n"
        f"- Status: `USER_SELECTED_FOR_ANALYSIS`\n"
        f"- Opportunity: **{row['title']}**\n"
        f"- Maximum advertised reward: `{row['reward_currency']} {row['reward_amount']}`\n"
        f"- Reward basis: `{row['reward_basis']}`\n"
        f"- Payment method: `{row['payment_method'] or 'REVIEW_REQUIRED'}`\n"
        f"- KYC required: `{row['kyc_required'] or 'REVIEW_REQUIRED'}`\n"
        f"- Truth status: `{status}`\n"
        f"- Reason: {row['truth_reason']}\n"
        f"- Execution path: `{row['execution_path']}`\n"
        f"- URL: {url}\n\n"
        "No claim, application, security test, submission, signature or payment was performed.\n",
        encoding="utf-8",
    )
    print(f"Registered dashboard selection #{issue_number}: {row['title']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
