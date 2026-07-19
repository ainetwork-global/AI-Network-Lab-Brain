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
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_CSV = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "04_OPPORTUNITIES"
    / "algora_official_active_bounties.csv"
)

REPORT_FILE = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "12_REPORTS"
    / "LATEST_ALGORA_OFFICIAL_DISCOVERY.md"
)

ALGORA_API_BASE = "https://console.algora.io/api"
ALGORA_COMMUNITY_URL = "https://app.algora.io"

MIN_REWARD_USD = 25.0
MAX_ORGANIZATIONS = 300
MAX_PAGES_PER_ORG = 20
REQUEST_TIMEOUT = 30
REQUEST_DELAY_SECONDS = 0.20

USER_AGENT = (
    "AI-Network-Lab-Brain/1.0 "
    "(canonical paid opportunity discovery)"
)

KNOWN_ORGANIZATIONS = [
    "calcom",
    "triggerdotdev",
    "formbricks",
    "twentyhq",
    "maybe-finance",
    "dubinc",
    "documenso",
    "medusajs",
    "openstatusHQ",
    "midday-ai",
    "unkeyed",
    "TypeCellOS",
    "highlight",
    "plunk",
    "usememos",
    "antiwork",
    "twentyhq",
]


def http_get_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json",
        },
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        raw = response.read().decode("utf-8")
        payload = json.loads(raw)

    if not isinstance(payload, dict):
        raise ValueError(f"Resposta inesperada em {url}")

    return payload


def http_get_text(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml",
        },
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT) as response:
        return response.read().decode("utf-8", errors="replace")


def discover_organizations() -> list[str]:
    organizations: set[str] = set(KNOWN_ORGANIZATIONS)

    try:
        html = http_get_text(ALGORA_COMMUNITY_URL)

        patterns = [
            r'app\.algora\.io/org/([A-Za-z0-9_.-]+)',
            r'app\.algora\.io/([A-Za-z0-9_.-]+)/bounties',
            r'"/org/([A-Za-z0-9_.-]+)"',
            r'"/([A-Za-z0-9_.-]+)/bounties"',
            r'"repo_owner"\s*:\s*"([^"]+)"',
            r'"organization"\s*:\s*"([^"]+)"',
        ]

        for pattern in patterns:
            for match in re.findall(pattern, html, flags=re.IGNORECASE):
                candidate = match.strip()

                if (
                    candidate
                    and candidate.lower()
                    not in {
                        "api",
                        "docs",
                        "login",
                        "signup",
                        "explore",
                        "settings",
                        "bounties",
                        "claims",
                    }
                ):
                    organizations.add(candidate)
    except Exception as exc:
        print(
            f"[WARN] Não foi possível extrair organizações da comunidade: {exc}",
            file=sys.stderr,
        )

    return sorted(organizations, key=str.lower)[:MAX_ORGANIZATIONS]


def list_org_bounties(org: str) -> list[dict[str, Any]]:
    collected: list[dict[str, Any]] = []
    cursor = ""

    for _ in range(MAX_PAGES_PER_ORG):
        params: dict[str, str | int] = {"limit": 100}

        if cursor:
            params["cursor"] = cursor

        url = (
            f"{ALGORA_API_BASE}/orgs/{org}/bounties?"
            + urlencode(params)
        )

        try:
            payload = http_get_json(url)
        except HTTPError as exc:
            if exc.code in {400, 401, 403, 404}:
                break
            raise
        except (URLError, TimeoutError):
            raise

        items = payload.get("items", [])

        if not isinstance(items, list):
            break

        for item in items:
            if isinstance(item, dict):
                collected.append(item)

        next_cursor = payload.get("next_cursor")

        if not next_cursor or not items:
            break

        cursor = str(next_cursor)
        time.sleep(REQUEST_DELAY_SECONDS)

    return collected


def github_issue_live(
    repository: str,
    issue_number: int,
) -> dict[str, Any] | None:
    command = [
        "gh",
        "issue",
        "view",
        str(issue_number),
        "--repo",
        repository,
        "--json",
        (
            "number,title,body,state,url,comments,"
            "createdAt,updatedAt,labels,assignees"
        ),
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=45,
            check=False,
        )
    except Exception as exc:
        print(
            f"[WARN] GitHub lookup falhou para "
            f"{repository}#{issue_number}: {exc}",
            file=sys.stderr,
        )
        return None

    if result.returncode != 0 or not result.stdout.strip():
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, dict) else None


def count_competition(issue: dict[str, Any]) -> dict[str, int]:
    comments = issue.get("comments", [])

    if not isinstance(comments, list):
        comments = []

    comment_text = "\n".join(
        str(comment.get("body", ""))
        for comment in comments
        if isinstance(comment, dict)
    )

    attempt_patterns = (
        r"(?i)/attempt",
        r"(?i)/claim",
        r"(?i)\bclaiming\b",
        r"(?i)\bworking on\b",
        r"(?i)\bstarted working\b",
        r"(?i)\bsubmitted\b",
        r"(?i)\bpull request\b",
        r"(?i)\bmy solution\b",
    )

    attempt_count = sum(
        1
        for comment in comments
        if isinstance(comment, dict)
        and any(
            re.search(pattern, str(comment.get("body", "")))
            for pattern in attempt_patterns
        )
    )

    pr_numbers: set[str] = set()

    for match in re.finditer(
        r"(?i)github\.com/[^/\s]+/[^/\s]+/pull/([0-9]+)",
        comment_text,
    ):
        pr_numbers.add(match.group(1))

    for match in re.finditer(
        r"(?i)\bPR\s*#?\s*([0-9]+)\b",
        comment_text,
    ):
        pr_numbers.add(match.group(1))

    competition_score = min(60, len(pr_numbers) * 12)
    competition_score += min(40, attempt_count * 8)

    return {
        "comment_count": len(comments),
        "attempt_count": attempt_count,
        "pr_reference_count": len(pr_numbers),
        "competition_score": competition_score,
    }


def normalize_bounty(
    org: str,
    bounty: dict[str, Any],
) -> dict[str, Any] | None:
    if str(bounty.get("status", "")).lower() != "active":
        return None

    amount_cents = bounty.get("amount")

    try:
        reward_usd = float(amount_cents) / 100.0
    except (TypeError, ValueError):
        return None

    if reward_usd < MIN_REWARD_USD:
        return None

    repo_owner = str(bounty.get("repo_owner", "")).strip()
    repo_name = str(bounty.get("repo_name", "")).strip()
    issue_number = bounty.get("number")

    if not repo_owner or not repo_name:
        return None

    try:
        issue_number_int = int(issue_number)
    except (TypeError, ValueError):
        return None

    repository = f"{repo_owner}/{repo_name}"
    issue = github_issue_live(repository, issue_number_int)

    if not issue:
        return None

    if str(issue.get("state", "")).upper() != "OPEN":
        return None

    competition = count_competition(issue)

    if competition["competition_score"] >= 10:
        competition_level = (
            "SATURATED"
            if competition["competition_score"] >= 50
            else "HIGH"
            if competition["competition_score"] >= 25
            else "MODERATE"
        )
    else:
        competition_level = "LOW"

    title = str(issue.get("title", "")).strip()
    body = str(issue.get("body", "") or "").strip()
    issue_url = str(issue.get("url", "")).strip()

    estimated_hours = 8.0

    return {
        "source_name": "algora_official_api",
        "source_type": "canonical_bounty_platform",
        "platform": "Algora",
        "canonical_payment_source": "true",
        "payment_platform_verified": "true",
        "bounty_id": str(bounty.get("id", "")),
        "repository": repository,
        "issue_number": issue_number_int,
        "title": title,
        "description": body,
        "url": issue_url,
        "issue_url": issue_url,
        "reward": reward_usd,
        "reward_usd": reward_usd,
        "amount_usd": reward_usd,
        "currency": str(bounty.get("currency", "USD")),
        "status": "open",
        "bounty_status": "active",
        "payment_terms": (
            f"Algora active bounty reward USD {reward_usd:.2f} "
            "paid to solver for accepted task"
        ),
        "executor_payment_evidence": (
            "Official Algora API active bounty amount"
        ),
        "estimated_hours": estimated_hours,
        "estimated_revenue_per_hour": round(
            reward_usd / estimated_hours,
            2,
        ),
        "comments": competition["comment_count"],
        "attempts": competition["attempt_count"],
        "pull_requests": competition["pr_reference_count"],
        "competition_score_live": competition["competition_score"],
        "competition_level_live": competition_level,
        "created_at": str(bounty.get("created_at", "")),
        "updated_at": str(bounty.get("updated_at", "")),
        "issue_updated_at": str(issue.get("updatedAt", "")),
        "organization_discovered": org,
        "discovered_at": datetime.now(timezone.utc).isoformat(),
    }


def write_csv(rows: list[dict[str, Any]]) -> None:
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)

    fields = [
        "source_name",
        "source_type",
        "platform",
        "canonical_payment_source",
        "payment_platform_verified",
        "bounty_id",
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
        "created_at",
        "updated_at",
        "issue_updated_at",
        "organization_discovered",
        "discovered_at",
    ]

    with OUTPUT_CSV.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def write_report(
    organizations: list[str],
    total_api_items: int,
    rows: list[dict[str, Any]],
    errors: list[str],
) -> None:
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)

    low_competition = [
        row
        for row in rows
        if row["competition_level_live"] == "LOW"
    ]

    lines = [
        "# Latest Algora Official Discovery",
        "",
        f"- Generated at: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Organizations checked: **{len(organizations)}**",
        f"- API bounty records received: **{total_api_items}**",
        f"- Active canonical bounties >= USD {MIN_REWARD_USD:.0f}: "
        f"**{len(rows)}**",
        f"- Low-competition candidates: **{len(low_competition)}**",
        f"- Errors: **{len(errors)}**",
        "",
        "## Top candidates",
        "",
        "| Reward | Repository | Issue | Competition | Title |",
        "|---:|---|---:|---|---|",
    ]

    ranked = sorted(
        rows,
        key=lambda row: (
            row["competition_level_live"] == "LOW",
            float(row["reward_usd"]),
        ),
        reverse=True,
    )

    for row in ranked[:30]:
        title = str(row["title"]).replace("|", "/")
        lines.append(
            f"| ${float(row['reward_usd']):.2f} | "
            f"{row['repository']} | "
            f"{row['issue_number']} | "
            f"{row['competition_level_live']} | "
            f"{title} |"
        )

    if errors:
        lines.extend(
            [
                "",
                "## Errors",
                "",
            ]
        )

        lines.extend(f"- {error}" for error in errors[:50])

    REPORT_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    organizations = discover_organizations()
    normalized_rows: list[dict[str, Any]] = []
    errors: list[str] = []
    total_api_items = 0
    seen: set[str] = set()

    print("===== ALGORA OFFICIAL API DISCOVERY =====")
    print(f"Organizations queued: {len(organizations)}")

    for index, org in enumerate(organizations, 1):
        print(
            f"[{index}/{len(organizations)}] "
            f"Checking Algora org: {org}"
        )

        try:
            bounties = list_org_bounties(org)
        except Exception as exc:
            errors.append(f"{org}: {exc}")
            continue

        total_api_items += len(bounties)

        for bounty in bounties:
            row = normalize_bounty(org, bounty)

            if not row:
                continue

            key = (
                f"{str(row['repository']).lower()}"
                f"#{row['issue_number']}"
            )

            if key in seen:
                continue

            seen.add(key)
            normalized_rows.append(row)

        time.sleep(REQUEST_DELAY_SECONDS)

    normalized_rows.sort(
        key=lambda row: (
            row["competition_level_live"] == "LOW",
            float(row["reward_usd"]),
        ),
        reverse=True,
    )

    write_csv(normalized_rows)
    write_report(
        organizations,
        total_api_items,
        normalized_rows,
        errors,
    )

    print("")
    print("===== ALGORA OFFICIAL DISCOVERY RESULT =====")
    print(f"Organizations checked: {len(organizations)}")
    print(f"API records received: {total_api_items}")
    print(f"Eligible active bounties: {len(normalized_rows)}")
    print(
        "Low competition: "
        + str(
            sum(
                1
                for row in normalized_rows
                if row["competition_level_live"] == "LOW"
            )
        )
    )
    print(f"Errors: {len(errors)}")
    print(f"CSV: {OUTPUT_CSV}")
    print(f"Report: {REPORT_FILE}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
