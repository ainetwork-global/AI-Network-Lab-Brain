import csv
import json
import os
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

INPUT = ROOT / "04_OPPORTUNITIES" / "execution_candidate_ranking.csv"
OUTPUT = ROOT / "04_OPPORTUNITIES" / "live_validated_opportunities.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_LIVE_OPPORTUNITY_VALIDATION.md"

API_ROOT = "https://api.github.com"

TOKEN = (
    os.getenv("GITHUB_TOKEN")
    or os.getenv("GH_TOKEN")
    or ""
).strip()

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "GlobalRevenueBrain-LiveValidator",
    "X-GitHub-Api-Version": "2022-11-28",
}

if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

OUTPUT_FIELDS = [
    "validated_at",
    "rank_position",
    "is_current_best_target",
    "title",
    "organization",
    "repository",
    "issue_number",
    "source_url",
    "reward_currency",
    "reward_amount",
    "payment_probability",
    "final_execution_score",
    "recommended_action",
    "github_state",
    "is_open",
    "is_locked",
    "assignee_count",
    "assignees",
    "comment_count",
    "labels",
    "reward_mentioned_live",
    "reward_evidence",
    "claim_signal",
    "claim_evidence",
    "completion_signal",
    "completion_evidence",
    "repository_archived",
    "repository_disabled",
    "repository_visibility",
    "live_validation_score",
    "live_validation_status",
    "validation_reason",
    "api_error",
]

def text(value):
    return str(value or "").strip()

def number(value, default=0.0):
    try:
        return float(text(value))
    except (TypeError, ValueError):
        return default

def integer(value, default=0):
    try:
        return int(float(text(value)))
    except (TypeError, ValueError):
        return default

def github_get(path):
    url = f"{API_ROOT}{path}"
    request = urllib.request.Request(url, headers=HEADERS)

    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return json.loads(response.read().decode("utf-8")), ""
    except urllib.error.HTTPError as exc:
        try:
            body = exc.read().decode("utf-8", errors="replace")
        except Exception:
            body = ""
        return None, f"HTTP {exc.code}: {body[:300]}"
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"

def normalize_money(value):
    value = number(value)
    if value.is_integer():
        return str(int(value))
    return f"{value:.2f}"

def find_reward_evidence(body, title, currency, reward_amount):
    haystack = f"{title}\n{body}".lower()
    amount = normalize_money(reward_amount)

    currency_tokens = {
        "USD": ["usd", "$", "dollar", "dollars"],
        "EUR": ["eur", "€", "euro", "euros"],
        "GBP": ["gbp", "£", "pound", "pounds"],
        "USDC": ["usdc"],
        "USDT": ["usdt"],
        "BTC": ["btc", "bitcoin"],
        "ETH": ["eth", "ethereum"],
    }

    amount_patterns = {
        amount,
        amount.replace(".", ","),
        f"{reward_amount:.2f}",
        f"{reward_amount:,.2f}",
    }

    amount_found = any(pattern.lower() in haystack for pattern in amount_patterns)

    tokens = currency_tokens.get(
        text(currency).upper(),
        [text(currency).lower()]
    )

    currency_found = any(token and token in haystack for token in tokens)

    evidence_lines = []

    for line in f"{title}\n{body}".splitlines():
        lowered = line.lower()

        if any(pattern.lower() in lowered for pattern in amount_patterns):
            evidence_lines.append(line.strip())

        if len(evidence_lines) >= 3:
            break

    reward_mentioned = amount_found and currency_found

    return reward_mentioned, " | ".join(evidence_lines)[:800]

def detect_signals(issue, comments):
    combined_parts = [
        text(issue.get("title")),
        text(issue.get("body")),
    ]

    for comment in comments:
        combined_parts.append(text(comment.get("body")))

    combined = "\n".join(combined_parts)
    lowered = combined.lower()

    claim_patterns = [
        r"\bclaim(?:ed|ing)?\b",
        r"\bassign(?:ed|ment)?\b",
        r"\bi(?:'|’)ll work on this\b",
        r"\bi am working on this\b",
        r"\bworking on this\b",
        r"\bcan i take this\b",
        r"\bplease assign\b",
        r"\breserve(?:d)?\b",
        r"\btaken\b",
    ]

    completion_patterns = [
        r"\bcompleted\b",
        r"\bdone\b",
        r"\bmerged\b",
        r"\bpaid\b",
        r"\breward sent\b",
        r"\bbounty paid\b",
        r"\bresolved\b",
        r"\bfixed in\b",
    ]

    claim_matches = []
    completion_matches = []

    for line in combined.splitlines():
        clean = line.strip()

        if not clean:
            continue

        lowered_line = clean.lower()

        if any(re.search(pattern, lowered_line) for pattern in claim_patterns):
            claim_matches.append(clean)

        if any(re.search(pattern, lowered_line) for pattern in completion_patterns):
            completion_matches.append(clean)

        if len(claim_matches) >= 3 and len(completion_matches) >= 3:
            break

    return (
        bool(claim_matches),
        " | ".join(claim_matches[:3])[:800],
        bool(completion_matches),
        " | ".join(completion_matches[:3])[:800],
    )

def compute_status(
    issue,
    repository,
    reward_mentioned,
    claim_signal,
    completion_signal,
    api_error,
):
    if api_error:
        return 25.0, "HUMAN_REVIEW_REQUIRED", "GitHub API validation failed"

    score = 0.0
    reasons = []

    state = text(issue.get("state")).lower()
    is_open = state == "open"

    if is_open:
        score += 35
        reasons.append("issue_open")
    else:
        reasons.append("issue_closed")

    if not repository.get("archived", False):
        score += 15
        reasons.append("repository_active")
    else:
        reasons.append("repository_archived")

    if not repository.get("disabled", False):
        score += 10
    else:
        reasons.append("repository_disabled")

    if reward_mentioned:
        score += 25
        reasons.append("reward_confirmed_live")
    else:
        reasons.append("reward_not_confirmed_in_live_content")

    assignees = issue.get("assignees") or []

    if not assignees:
        score += 10
        reasons.append("no_assignee")
    else:
        reasons.append("already_assigned")

    if not claim_signal:
        score += 5
        reasons.append("no_claim_signal")
    else:
        reasons.append("claim_signal_detected")

    if completion_signal:
        score -= 35
        reasons.append("completion_signal_detected")

    score = max(0.0, min(100.0, score))

    if not is_open:
        status = "INVALID"
    elif repository.get("archived") or repository.get("disabled"):
        status = "INVALID"
    elif completion_signal:
        status = "INVALID"
    elif reward_mentioned and not assignees and not claim_signal and score >= 80:
        status = "READY_TO_EXECUTE"
    else:
        status = "HUMAN_REVIEW_REQUIRED"

    return score, status, ";".join(reasons)

if not INPUT.exists():
    raise FileNotFoundError(f"Ranking não encontrado: {INPUT}")

with INPUT.open("r", encoding="utf-8-sig", newline="") as file:
    candidates = list(csv.DictReader(file))

candidates.sort(
    key=lambda row: integer(row.get("rank_position"), 999999)
)

validated = []
validated_at = datetime.now(timezone.utc).isoformat()

for candidate in candidates:
    repository_name = text(candidate.get("repository"))
    issue_number = integer(candidate.get("issue_number"))

    print()
    print("-" * 70)
    print(
        f"Validando rank {candidate.get('rank_position')}: "
        f"{repository_name}#{issue_number}"
    )

    issue = {}
    repository = {}
    comments = []
    errors = []

    if not repository_name or not issue_number:
        errors.append("repository_or_issue_missing")
    else:
        repository, repository_error = github_get(
            f"/repos/{repository_name}"
        )

        if repository_error:
            errors.append(repository_error)
            repository = {}

        issue, issue_error = github_get(
            f"/repos/{repository_name}/issues/{issue_number}"
        )

        if issue_error:
            errors.append(issue_error)
            issue = {}

        if issue:
            comments_url = (
                f"/repos/{repository_name}/issues/"
                f"{issue_number}/comments?per_page=100"
            )

            comments_data, comments_error = github_get(comments_url)

            if comments_error:
                errors.append(comments_error)
            elif isinstance(comments_data, list):
                comments = comments_data

    api_error = " | ".join(errors)

    reward_mentioned, reward_evidence = find_reward_evidence(
        text(issue.get("body")),
        text(issue.get("title")),
        text(candidate.get("reward_currency")),
        number(candidate.get("reward_amount")),
    )

    (
        claim_signal,
        claim_evidence,
        completion_signal,
        completion_evidence,
    ) = detect_signals(issue, comments)

    live_score, live_status, validation_reason = compute_status(
        issue,
        repository,
        reward_mentioned,
        claim_signal,
        completion_signal,
        api_error,
    )

    assignees = [
        text(person.get("login"))
        for person in (issue.get("assignees") or [])
        if person.get("login")
    ]

    labels = [
        text(label.get("name"))
        for label in (issue.get("labels") or [])
        if isinstance(label, dict)
    ]

    result = {
        "validated_at": validated_at,
        "rank_position": candidate.get("rank_position", ""),
        "is_current_best_target": candidate.get(
            "is_current_best_target", ""
        ),
        "title": candidate.get("title", ""),
        "organization": candidate.get("organization", ""),
        "repository": repository_name,
        "issue_number": issue_number,
        "source_url": candidate.get("source_url", ""),
        "reward_currency": candidate.get("reward_currency", ""),
        "reward_amount": candidate.get("reward_amount", ""),
        "payment_probability": candidate.get(
            "payment_probability", ""
        ),
        "final_execution_score": candidate.get(
            "final_execution_score", ""
        ),
        "recommended_action": candidate.get(
            "recommended_action", ""
        ),
        "github_state": issue.get("state", ""),
        "is_open": str(text(issue.get("state")).lower() == "open").lower(),
        "is_locked": str(bool(issue.get("locked", False))).lower(),
        "assignee_count": len(assignees),
        "assignees": ";".join(assignees),
        "comment_count": issue.get("comments", len(comments)),
        "labels": ";".join(labels),
        "reward_mentioned_live": str(reward_mentioned).lower(),
        "reward_evidence": reward_evidence,
        "claim_signal": str(claim_signal).lower(),
        "claim_evidence": claim_evidence,
        "completion_signal": str(completion_signal).lower(),
        "completion_evidence": completion_evidence,
        "repository_archived": str(
            bool(repository.get("archived", False))
        ).lower(),
        "repository_disabled": str(
            bool(repository.get("disabled", False))
        ).lower(),
        "repository_visibility": repository.get("visibility", ""),
        "live_validation_score": round(live_score, 2),
        "live_validation_status": live_status,
        "validation_reason": validation_reason,
        "api_error": api_error,
    }

    validated.append(result)

    print("Status GitHub:", result["github_state"])
    print("Reward confirmado:", result["reward_mentioned_live"])
    print("Assignees:", result["assignee_count"])
    print("Claim signal:", result["claim_signal"])
    print("Completion signal:", result["completion_signal"])
    print("Live score:", result["live_validation_score"])
    print("Resultado:", result["live_validation_status"])

    time.sleep(0.5)

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

with OUTPUT.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
    writer.writeheader()
    writer.writerows(validated)

status_order = {
    "READY_TO_EXECUTE": 0,
    "HUMAN_REVIEW_REQUIRED": 1,
    "INVALID": 2,
}

validated.sort(
    key=lambda row: (
        status_order.get(row["live_validation_status"], 9),
        -number(row["live_validation_score"]),
        integer(row["rank_position"], 999999),
    )
)

report_lines = [
    "# LIVE OPPORTUNITY VALIDATION",
    "",
    f"Generated at: {validated_at}",
    "",
    f"Candidates validated: {len(validated)}",
    "",
]

for row in validated:
    report_lines.extend([
        f"## Rank {row['rank_position']} — {row['title']}",
        "",
        f"- Repository: `{row['repository']}`",
        f"- Issue: `{row['issue_number']}`",
        f"- Reward: `{row['reward_currency']} {row['reward_amount']}`",
        f"- GitHub state: `{row['github_state']}`",
        f"- Reward confirmed live: `{row['reward_mentioned_live']}`",
        f"- Assignees: `{row['assignee_count']}`",
        f"- Claim signal: `{row['claim_signal']}`",
        f"- Completion signal: `{row['completion_signal']}`",
        f"- Live validation score: `{row['live_validation_score']}`",
        f"- Status: `{row['live_validation_status']}`",
        f"- Reason: `{row['validation_reason']}`",
        f"- URL: {row['source_url']}",
        "",
    ])

REPORT.parent.mkdir(parents=True, exist_ok=True)
REPORT.write_text(
    "\n".join(report_lines),
    encoding="utf-8-sig",
)

print()
print("=" * 70)
print("LIVE OPPORTUNITY VALIDATION CONCLUÍDA")
print("=" * 70)
print("Candidatos:", len(validated))
print("CSV:", OUTPUT)
print("Relatório:", REPORT)

if validated:
    print()
    print("Melhor resultado validado:")
    print("Título:", validated[0]["title"])
    print("Status:", validated[0]["live_validation_status"])
    print("Score:", validated[0]["live_validation_score"])
    print("URL:", validated[0]["source_url"])
