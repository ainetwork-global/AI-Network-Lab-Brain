from __future__ import annotations

import csv
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]

ORG_CSV = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "04_OPPORTUNITIES"
    / "algora_discovered_organizations.csv"
)

BOUNTY_CSV = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "04_OPPORTUNITIES"
    / "algora_official_active_bounties.csv"
)

REPORT_FILE = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "12_REPORTS"
    / "LATEST_ALGORA_DYNAMIC_DISCOVERY.md"
)

ALGORA_API = "https://console.algora.io/api"
MIN_REWARD_USD = 25.0
REQUEST_TIMEOUT = 30
MAX_SEARCH_RESULTS = 1000

SEARCH_QUERIES = [
    '"algora.io" is:issue is:open',
    '"app.algora.io" is:issue is:open',
    '"console.algora.io" is:issue is:open',
    '"Algora bounty" is:issue is:open',
    '"Algora" "bounty" is:issue is:open',
    '"bounty" "reward" is:issue is:open',
]


def run_json(command: list[str]) -> Any:
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=False,
    )

    if result.returncode != 0:
        return None

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return None


def github_search(query: str) -> list[dict[str, Any]]:
    payload = run_json(
        [
            "gh",
            "search",
            "issues",
            query,
            "--limit",
            str(MAX_SEARCH_RESULTS),
            "--json",
            "repository,number,title,url,state,body,commentsCount,updatedAt",
        ]
    )

    return payload if isinstance(payload, list) else []


def github_issue(repository: str, number: int) -> dict[str, Any] | None:
    payload = run_json(
        [
            "gh",
            "issue",
            "view",
            str(number),
            "--repo",
            repository,
            "--json",
            "number,title,body,state,url,comments,updatedAt",
        ]
    )

    return payload if isinstance(payload, dict) else None


def api_get(url: str) -> dict[str, Any] | None:
    request = Request(
        url,
        headers={
            "User-Agent": "AI-Network-Lab-Brain/1.0",
            "Accept": "application/json",
        },
    )

    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        if exc.code in {400, 401, 403, 404}:
            return None
        raise
    except Exception:
        return None

    return payload if isinstance(payload, dict) else None


def list_bounties(org: str) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    cursor = ""

    for _ in range(20):
        params: dict[str, str | int] = {"limit": 100}

        if cursor:
            params["cursor"] = cursor

        url = (
            f"{ALGORA_API}/orgs/{org}/bounties?"
            + urlencode(params)
        )

        payload = api_get(url)

        if not payload:
            break

        items = payload.get("items", [])

        if not isinstance(items, list):
            break

        collected.extend(
            item for item in items if isinstance(item, dict)
        )

        cursor = str(payload.get("next_cursor", "") or "")

        if not cursor or not items:
            break

        time.sleep(0.15)

    return collected


def extract_repository(item: dict[str, Any]) -> str:
    repository = item.get("repository")

    if isinstance(repository, dict):
        name = str(
            repository.get("nameWithOwner")
            or repository.get("name_with_owner")
            or ""
        ).strip()

        if name:
            return name

    url = str(item.get("url", ""))

    match = re.search(
        r"github\.com/([^/\s]+)/([^/\s]+)/issues/",
        url,
        flags=re.IGNORECASE,
    )

    if match:
        return f"{match.group(1)}/{match.group(2)}"

    return ""


def competition(issue: dict[str, Any]) -> dict[str, int | str]:
    comments = issue.get("comments", [])

    if not isinstance(comments, list):
        comments = []

    attempts = 0
    pr_numbers: set[str] = set()

    patterns = (
        r"/attempt",
        r"/claim",
        r"\bclaiming\b",
        r"\bclaim this\b",
        r"\bworking on\b",
        r"\bstarted working\b",
        r"\bsubmitted\b",
        r"\bmy solution\b",
        r"\bpull request\b",
    )

    for comment in comments:
        if not isinstance(comment, dict):
            continue

        body = str(comment.get("body", ""))

        if any(
            re.search(pattern, body, flags=re.IGNORECASE)
            for pattern in patterns
        ):
            attempts += 1

        for match in re.finditer(
            r"github\.com/[^/\s]+/[^/\s]+/pull/([0-9]+)",
            body,
            flags=re.IGNORECASE,
        ):
            pr_numbers.add(match.group(1))

        for match in re.finditer(
            r"\bPR\s*#?\s*([0-9]+)\b",
            body,
            flags=re.IGNORECASE,
        ):
            pr_numbers.add(match.group(1))

    score = min(60, len(pr_numbers) * 12)
    score += min(40, attempts * 8)

    if score >= 50:
        level = "SATURATED"
    elif score >= 25:
        level = "HIGH"
    elif score >= 10:
        level = "MODERATE"
    else:
        level = "LOW"

    return {
        "comments": len(comments),
        "attempts": attempts,
        "pull_requests": len(pr_numbers),
        "score": score,
        "level": level,
    }


def main() -> int:
    discovered_repositories: dict[str, dict[str, Any]] = {}
    search_rows = 0

    print("===== ALGORA GITHUB ORGANIZATION DISCOVERY =====")

    for query in SEARCH_QUERIES:
        print(f"Searching: {query}")

        rows = github_search(query)
        search_rows += len(rows)

        for row in rows:
            repository = extract_repository(row)

            if not repository or "/" not in repository:
                continue

            owner = repository.split("/", 1)[0]

            current = discovered_repositories.setdefault(
                repository.lower(),
                {
                    "repository": repository,
                    "owner": owner,
                    "search_hits": 0,
                    "algora_signal": False,
                },
            )

            current["search_hits"] += 1

            text = " ".join(
                [
                    str(row.get("title", "")),
                    str(row.get("body", "")),
                    str(row.get("url", "")),
                ]
            )

            if re.search(r"algora", text, flags=re.IGNORECASE):
                current["algora_signal"] = True

    owners = {
        str(row["owner"])
        for row in discovered_repositories.values()
    }

    # Inclui a organização usada no exemplo da documentação oficial
    # para confirmar se o endpoint continua operacional.
    owners.add("Uber4Coding")

    org_rows: list[dict[str, Any]] = []
    bounty_rows: list[dict[str, Any]] = []
    seen_bounties: set[str] = set()

    print(f"Owners discovered: {len(owners)}")

    for index, owner in enumerate(sorted(owners), 1):
        print(f"[{index}/{len(owners)}] Checking Algora org: {owner}")

        bounties = list_bounties(owner)

        org_rows.append(
            {
                "organization": owner,
                "api_bounty_count": len(bounties),
                "checked_at": datetime.now(timezone.utc).isoformat(),
            }
        )

        for bounty in bounties:
            if str(bounty.get("status", "")).lower() != "active":
                continue

            try:
                reward_usd = float(bounty.get("amount", 0)) / 100.0
                issue_number = int(bounty.get("number"))
            except (TypeError, ValueError):
                continue

            if reward_usd < MIN_REWARD_USD:
                continue

            repo_owner = str(bounty.get("repo_owner", "")).strip()
            repo_name = str(bounty.get("repo_name", "")).strip()

            if not repo_owner or not repo_name:
                continue

            repository = f"{repo_owner}/{repo_name}"
            key = f"{repository.lower()}#{issue_number}"

            if key in seen_bounties:
                continue

            live = github_issue(repository, issue_number)

            if not live:
                continue

            if str(live.get("state", "")).upper() != "OPEN":
                continue

            seen_bounties.add(key)
            comp = competition(live)

            bounty_rows.append(
                {
                    "source_name": "algora_official_api",
                    "source_type": "canonical_bounty_platform",
                    "platform": "Algora",
                    "canonical_payment_source": "true",
                    "payment_platform_verified": "true",
                    "repository": repository,
                    "issue_number": issue_number,
                    "title": str(live.get("title", "")),
                    "description": str(live.get("body", "") or ""),
                    "url": str(live.get("url", "")),
                    "issue_url": str(live.get("url", "")),
                    "reward": reward_usd,
                    "reward_usd": reward_usd,
                    "amount_usd": reward_usd,
                    "currency": str(bounty.get("currency", "USD")),
                    "status": "open",
                    "bounty_status": "active",
                    "payment_terms": (
                        f"Official Algora bounty USD {reward_usd:.2f} "
                        "payable to accepted solver"
                    ),
                    "executor_payment_evidence": (
                        "Official Algora public API active bounty"
                    ),
                    "estimated_hours": 8,
                    "estimated_revenue_per_hour": round(
                        reward_usd / 8,
                        2,
                    ),
                    "comments": comp["comments"],
                    "attempts": comp["attempts"],
                    "pull_requests": comp["pull_requests"],
                    "competition_score_live": comp["score"],
                    "competition_level_live": comp["level"],
                    "organization_discovered": owner,
                    "discovered_at": datetime.now(timezone.utc).isoformat(),
                }
            )

        time.sleep(0.10)

    ORG_CSV.parent.mkdir(parents=True, exist_ok=True)

    with ORG_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        fields = [
            "organization",
            "api_bounty_count",
            "checked_at",
        ]

        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(org_rows)

    bounty_rows.sort(
        key=lambda row: (
            row["competition_level_live"] == "LOW",
            float(row["reward_usd"]),
        ),
        reverse=True,
    )

    bounty_fields = [
        "source_name",
        "source_type",
        "platform",
        "canonical_payment_source",
        "payment_platform_verified",
        "repository",
        "issue_number",
        "title",
        "description",
        "url",
        "issue_url",
        "reward",
        "reward_usd",
        "amount_usd",
        "currency",
        "status",
        "bounty_status",
        "payment_terms",
        "executor_payment_evidence",
        "estimated_hours",
        "estimated_revenue_per_hour",
        "comments",
        "attempts",
        "pull_requests",
        "competition_score_live",
        "competition_level_live",
        "organization_discovered",
        "discovered_at",
    ]

    with BOUNTY_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=bounty_fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(bounty_rows)

    low = [
        row
        for row in bounty_rows
        if row["competition_level_live"] == "LOW"
    ]

    lines = [
        "# Latest Algora Dynamic Discovery",
        "",
        f"- Generated: `{datetime.now(timezone.utc).isoformat()}`",
        f"- GitHub search rows: **{search_rows}**",
        f"- Repositories discovered: **{len(discovered_repositories)}**",
        f"- Organizations checked: **{len(owners)}**",
        f"- Active canonical bounties >= USD 25: **{len(bounty_rows)}**",
        f"- Low competition: **{len(low)}**",
        "",
        "## Results",
        "",
        "| Reward | Repository | Issue | Competition | Title |",
        "|---:|---|---:|---|---|",
    ]

    for row in bounty_rows[:30]:
        title = str(row["title"]).replace("|", "/")

        lines.append(
            f"| ${float(row['reward_usd']):.2f} | "
            f"{row['repository']} | "
            f"{row['issue_number']} | "
            f"{row['competition_level_live']} | "
            f"{title} |"
        )

    REPORT_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    print("")
    print("===== ALGORA DYNAMIC DISCOVERY RESULT =====")
    print(f"GitHub search rows: {search_rows}")
    print(f"Repositories discovered: {len(discovered_repositories)}")
    print(f"Organizations checked: {len(owners)}")
    print(f"Active canonical bounties: {len(bounty_rows)}")
    print(f"Low competition: {len(low)}")
    print(f"Organization CSV: {ORG_CSV}")
    print(f"Bounty CSV: {BOUNTY_CSV}")
    print(f"Report: {REPORT_FILE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
