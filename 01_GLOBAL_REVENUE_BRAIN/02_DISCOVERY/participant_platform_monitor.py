from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "04_OPPORTUNITIES" / "participant_platform_status.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_PARTICIPANT_PLATFORM_MONITOR.md"
STATE = ROOT / "00_CURRENT_STATE" / "PARTICIPANT_PLATFORM_MONITOR_STATE.md"
TIMEOUT = 20

PLATFORMS: list[dict[str, str]] = [
    {"name": "CleverX", "url": "https://cleverx.com/", "category": "research_participant", "brazil": "unknown", "feed": "authenticated", "payment": "study incentive"},
    {"name": "Respondent", "url": "https://app.respondent.io/respondents/v2/projects/browse", "category": "research_participant", "brazil": "verified", "feed": "authenticated", "payment": "Tremendous or available platform method"},
    {"name": "User Interviews", "url": "https://www.userinterviews.com/hello", "category": "research_participant", "brazil": "possible", "feed": "authenticated", "payment": "study incentive"},
    {"name": "dscout", "url": "https://dscout.com/participate-in-research-studies", "category": "research_participant", "brazil": "possible", "feed": "mobile_app", "payment": "PayPal"},
    {"name": "UserTesting", "url": "https://www.usertesting.com/get-paid-to-test", "category": "usability_testing", "brazil": "verified_partial", "feed": "authenticated", "payment": "displayed per test"},
    {"name": "Prolific", "url": "https://app.prolific.com/studies", "category": "research_studies", "brazil": "verified", "feed": "authenticated", "payment": "platform balance"},
    {"name": "PlaybookUX", "url": "https://www.playbookux.com/participant-platform/", "category": "usability_testing", "brazil": "possible", "feed": "authenticated", "payment": "PayPal"},
    {"name": "Userlytics", "url": "https://www.userlytics.com/user-experience-research/paid-ux-testing/", "category": "usability_testing", "brazil": "possible", "feed": "authenticated", "payment": "test incentive"},
    {"name": "Userfeel", "url": "https://www.userfeel.com/tester-faq", "category": "usability_testing", "brazil": "possible", "feed": "authenticated", "payment": "3-30 USD per test advertised"},
    {"name": "TestingTime", "url": "https://www.testingtime.com/en/become-a-paid-testuser/", "category": "research_participant", "brazil": "unknown", "feed": "invitation", "payment": "study incentive"},
    {"name": "Trymata", "url": "https://trymata.com/learn/tester-faq/", "category": "usability_testing", "brazil": "unknown", "feed": "authenticated", "payment": "test incentive"},
    {"name": "MetroOpinion", "url": "https://www.metroopinion.com/", "category": "paid_surveys", "brazil": "verified_local_site", "feed": "authenticated", "payment": "survey incentive"},
    {"name": "Outlier", "url": "https://outlier.ai/", "category": "ai_training", "brazil": "possible", "feed": "authenticated", "payment": "project rate"},
    {"name": "OneForma", "url": "https://www.oneforma.com/", "category": "ai_training", "brazil": "verified_global", "feed": "matched_authenticated", "payment": "twice monthly"},
    {"name": "Clickworker", "url": "https://www.clickworker.com/clickworker/", "category": "microtasks", "brazil": "possible", "feed": "authenticated", "payment": "task rate"},
    {"name": "TELUS Digital AI Community", "url": "https://jobs.telusdigital.com/en/search/cfm5/ai-community/jobs", "category": "ai_training", "brazil": "role_dependent", "feed": "public_jobs", "payment": "role rate"},
]


def check(url: str) -> tuple[str, int, str]:
    request = Request(url, headers={"User-Agent": "Global-Revenue-Brain/1.0 Mozilla/5.0"})
    try:
        with urlopen(request, timeout=TIMEOUT) as response:
            return "reachable", int(response.status), str(response.geturl())
    except HTTPError as exc:
        if exc.code in {401, 403, 429}:
            return "reachable_protected", exc.code, url
        return "http_error", exc.code, url
    except (URLError, TimeoutError) as exc:
        return "temporary_error", 0, f"{type(exc).__name__}: {exc}"


def write_csv(rows: list[dict[str, Any]]) -> None:
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    generated = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, Any]] = []
    for platform in PLATFORMS:
        status, code, detail = check(platform["url"])
        rows.append({
            **platform,
            "status": status,
            "http_status": code,
            "detail": detail,
            "monitor_mode": "public_jobs" if platform["feed"] == "public_jobs" else "account_or_email_required",
            "automation_boundary": "human_identity_and_individual_approval_required",
            "initial_cost_allowed": "false",
            "checked_at": generated,
        })
        print(f"{platform['name']}: {status} ({code})")

    write_csv(rows)
    reachable = sum(row["status"].startswith("reachable") for row in rows)
    private = sum(row["monitor_mode"] == "account_or_email_required" for row in rows)
    lines = [
        "# Participant Platform Monitor",
        "",
        f"Generated: `{generated}`",
        "",
        f"- Platforms monitored: **{len(rows)}**",
        f"- Public entry points reachable/protected: **{reachable}**",
        f"- Account, app or email feed required: **{private}**",
        "- Initial cost permitted: **no**",
        "- Automatic identity-based participation: **no**",
        "",
        "| Platform | Category | Brazil | Feed | Status | Action |",
        "|---|---|---|---|---|---|",
    ]
    for row in rows:
        action = "monitor public roles" if row["monitor_mode"] == "public_jobs" else "monitor account/email"
        lines.append(f"| {row['name']} | {row['category']} | {row['brazil']} | {row['feed']} | {row['status']} | {action} |")
    lines.extend([
        "", "## Safety boundary", "",
        "The Brain may detect and rank invitations, studies, tests and roles.",
        "Screeners, interviews, recordings, identity checks, applications and task answers require the account holder.",
        "No purchase, deposit, subscription, false demographic answer or impersonation is allowed.",
    ])
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    STATE.write_text(
        "# Participant Platform Monitor State\n\n"
        "Status: `ACTIVE_PUBLIC_AND_ACCOUNT_AWARE`\n\n"
        f"Last run: `{generated}`\n\n"
        f"Platforms: `{len(rows)}`\n\n"
        "Personalized feeds require account access or notification emails.\n"
        "Human identity actions remain individually controlled.\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
