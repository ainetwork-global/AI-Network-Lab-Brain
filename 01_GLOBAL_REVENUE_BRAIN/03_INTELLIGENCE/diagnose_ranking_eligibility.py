import ast
import csv
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OPP = ROOT / "04_OPPORTUNITIES"
REPORT = ROOT / "12_REPORTS" / "LATEST_RANKING_ELIGIBILITY_DIAGNOSIS.md"
JSON_OUTPUT = OPP / "RANKING_ELIGIBILITY_DIAGNOSIS.json"

VERIFIED = OPP / "verified_opportunities.csv"
RANKING = OPP / "execution_candidate_ranking.csv"
PROMOTED = OPP / "DISCOVERY_PROMOTED_QUEUE.csv"
EXECUTION = OPP / "GLOBAL_EXECUTION_QUEUE.csv"


def read_csv(path):
    if not path.exists():
        return [], []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)
        return list(reader.fieldnames or []), list(reader)


def clean(value):
    return str(value or "").strip()


def first(row, names):
    for name in names:
        value = clean(row.get(name))
        if value:
            return value
    return ""


def normalize_repository(row):
    organization = first(
        row,
        [
            "organization",
            "owner",
            "github_owner",
            "org",
        ],
    )

    repository = first(
        row,
        [
            "repository",
            "repository_name",
            "repo",
        ],
    )

    repository = repository.strip("/")

    if "/" in repository:
        parts = repository.split("/", 1)

        if not organization:
            organization = parts[0]

        repository = parts[1]

    return organization.lower(), repository.lower()


def identity(row):
    organization, repository = normalize_repository(row)

    issue = first(
        row,
        [
            "issue_number",
            "number",
            "issue",
            "task_id",
        ],
    )

    url = first(
        row,
        [
            "url",
            "issue_url",
            "source_url",
        ],
    ).lower().rstrip("/")

    if organization or repository or issue:
        return organization, repository, issue

    return "url", url, ""


def numeric(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


verified_fields, verified_rows = read_csv(VERIFIED)
ranking_fields, ranking_rows = read_csv(RANKING)
promoted_fields, promoted_rows = read_csv(PROMOTED)
execution_fields, execution_rows = read_csv(EXECUTION)

ranking_ids = {identity(row) for row in ranking_rows}
promoted_ids = {identity(row) for row in promoted_rows}
execution_ids = {identity(row) for row in execution_rows}

verified_in_ranking = []
verified_not_in_ranking = []

for row in verified_rows:
    if identity(row) in ranking_ids:
        verified_in_ranking.append(row)
    else:
        verified_not_in_ranking.append(row)

promoted_in_execution = promoted_ids & execution_ids
promoted_missing_execution = promoted_ids - execution_ids

status_fields = [
    "verification_status",
    "status",
    "economic_status",
    "feasibility_status",
    "execution_status",
    "decision",
]

reason_fields = [
    "verification_reason",
    "rejection_reason",
    "reason",
    "feasibility_reason",
    "decision_reason",
    "payment_verification_reason",
]

status_distribution_all = Counter()
status_distribution_ranked = Counter()
status_distribution_dropped = Counter()

reason_distribution_dropped = Counter()

for row in verified_rows:
    status = first(row, status_fields) or "UNKNOWN"
    status_distribution_all[status] += 1

for row in verified_in_ranking:
    status = first(row, status_fields) or "UNKNOWN"
    status_distribution_ranked[status] += 1

for row in verified_not_in_ranking:
    status = first(row, status_fields) or "UNKNOWN"
    status_distribution_dropped[status] += 1

    reason = first(row, reason_fields)

    if reason:
        for item in reason.replace("|", ";").split(";"):
            item = item.strip()
            if item:
                reason_distribution_dropped[item] += 1
    else:
        reason_distribution_dropped["NO_REASON_FIELD"] += 1

field_profiles = {}

for field in verified_fields:
    values = [
        clean(row.get(field))
        for row in verified_rows
        if clean(row.get(field))
    ]

    unique_values = Counter(values)

    numeric_values = [
        numeric(value)
        for value in values
    ]

    numeric_values = [
        value
        for value in numeric_values
        if value is not None
    ]

    profile = {
        "non_empty": len(values),
        "unique": len(unique_values),
        "top_values": unique_values.most_common(12),
    }

    if numeric_values:
        profile.update({
            "numeric_min": min(numeric_values),
            "numeric_max": max(numeric_values),
            "numeric_avg": (
                sum(numeric_values) / len(numeric_values)
            ),
        })

    field_profiles[field] = profile

ranking_script_candidates = list(
    ROOT.rglob("execution_candidate_ranking.py")
)

ranking_script = (
    ranking_script_candidates[0]
    if ranking_script_candidates
    else None
)

ranking_source = ""

if ranking_script:
    ranking_source = ranking_script.read_text(
        encoding="utf-8-sig",
        errors="replace",
    )

interesting_lines = []

if ranking_source:
    keywords = [
        "actionable",
        "approval_required",
        "rejected",
        "verification_status",
        "feasibility",
        "payment_probability",
        "reward",
        "continue",
        "return",
        "if ",
        "eligible",
        "minimum",
        "threshold",
    ]

    for number, line in enumerate(
        ranking_source.splitlines(),
        start=1,
    ):
        lowered = line.lower()

        if any(
            keyword.lower() in lowered
            for keyword in keywords
        ):
            interesting_lines.append({
                "line": number,
                "content": line.rstrip(),
            })

diagnosis = {
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "files": {
        "verified": str(VERIFIED),
        "ranking": str(RANKING),
        "promoted": str(PROMOTED),
        "execution": str(EXECUTION),
        "ranking_script": (
            str(ranking_script)
            if ranking_script
            else None
        ),
    },
    "counts": {
        "verified_rows": len(verified_rows),
        "verified_unique": len(
            {identity(row) for row in verified_rows}
        ),
        "ranking_rows": len(ranking_rows),
        "ranking_unique": len(ranking_ids),
        "verified_present_in_ranking": len(
            verified_in_ranking
        ),
        "verified_missing_from_ranking": len(
            verified_not_in_ranking
        ),
        "promoted_rows": len(promoted_rows),
        "promoted_unique": len(promoted_ids),
        "promoted_present_in_execution": len(
            promoted_in_execution
        ),
        "promoted_missing_from_execution": len(
            promoted_missing_execution
        ),
    },
    "verified_status_distribution": {
        "all": dict(status_distribution_all),
        "ranked": dict(status_distribution_ranked),
        "dropped": dict(status_distribution_dropped),
    },
    "dropped_reason_distribution": dict(
        reason_distribution_dropped
    ),
    "verified_field_profiles": field_profiles,
    "ranking_filter_source_lines": interesting_lines,
}

JSON_OUTPUT.write_text(
    json.dumps(
        diagnosis,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

lines = [
    "# RANKING ELIGIBILITY DIAGNOSIS",
    "",
    f"Generated: {diagnosis['generated_at']}",
    "",
    "## Core Counts",
    "",
    "| Metric | Count |",
    "|---|---:|",
    (
        "| Verified rows | "
        f"{len(verified_rows)} |"
    ),
    (
        "| Verified present in ranking | "
        f"{len(verified_in_ranking)} |"
    ),
    (
        "| Verified missing from ranking | "
        f"{len(verified_not_in_ranking)} |"
    ),
    (
        "| Promoted unique identities | "
        f"{len(promoted_ids)} |"
    ),
    (
        "| Promoted found in execution queue | "
        f"{len(promoted_in_execution)} |"
    ),
    (
        "| Promoted missing from execution queue | "
        f"{len(promoted_missing_execution)} |"
    ),
    "",
    "## Verification Status: All",
    "",
    "| Status | Count |",
    "|---|---:|",
]

for status, count in status_distribution_all.most_common():
    lines.append(f"| {status} | {count} |")

lines.extend([
    "",
    "## Verification Status: Entered Ranking",
    "",
    "| Status | Count |",
    "|---|---:|",
])

for status, count in status_distribution_ranked.most_common():
    lines.append(f"| {status} | {count} |")

lines.extend([
    "",
    "## Verification Status: Did Not Enter Ranking",
    "",
    "| Status | Count |",
    "|---|---:|",
])

for status, count in status_distribution_dropped.most_common():
    lines.append(f"| {status} | {count} |")

lines.extend([
    "",
    "## Drop Reasons",
    "",
    "| Reason | Count |",
    "|---|---:|",
])

for reason, count in reason_distribution_dropped.most_common():
    safe_reason = reason.replace("|", "/")
    lines.append(f"| {safe_reason} | {count} |")

lines.extend([
    "",
    "## Ranking Script Filter Lines",
    "",
    "| Line | Source |",
    "|---:|---|",
])

for item in interesting_lines:
    source = (
        item["content"]
        .replace("|", "/")
        .replace("`", "'")
    )

    lines.append(
        f"| {item['line']} | {source} |"
    )

lines.extend([
    "",
    "## Sample Verified Opportunities Missing From Ranking",
    "",
    (
        "| Organization | Repository | Issue | "
        "Status | Reward | Reason | Title |"
    ),
    "|---|---|---:|---|---:|---|---|",
])

for row in verified_not_in_ranking[:40]:
    organization, repository = normalize_repository(row)

    issue = first(
        row,
        ["issue_number", "number", "issue"],
    )

    status = first(row, status_fields) or "UNKNOWN"

    reward = first(
        row,
        [
            "reward",
            "reward_amount",
            "expected_cash_value",
            "amount",
        ],
    )

    reason = first(row, reason_fields).replace("|", "/")

    title = first(
        row,
        ["title", "task_title", "name"],
    ).replace("|", "/").replace("\n", " ")

    lines.append(
        f"| {organization} | {repository} | "
        f"{issue} | {status} | {reward} | "
        f"{reason} | {title} |"
    )

lines.extend([
    "",
    "## Promoted Identities Missing From Execution Queue",
    "",
    "| Organization | Repository | Issue |",
    "|---|---|---:|",
])

for organization, repository, issue in sorted(
    promoted_missing_execution
)[:50]:
    lines.append(
        f"| {organization} | {repository} | {issue} |"
    )

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT.write_text(
    "\n".join(lines) + "\n",
    encoding="utf-8",
)

print()
print("=" * 72)
print("RANKING ELIGIBILITY DIAGNOSIS")
print("=" * 72)
print("Verified:", len(verified_rows))
print("Entered ranking:", len(verified_in_ranking))
print("Missing from ranking:", len(verified_not_in_ranking))
print("Promoted:", len(promoted_ids))
print(
    "Promoted found in execution:",
    len(promoted_in_execution),
)
print(
    "Promoted missing from execution:",
    len(promoted_missing_execution),
)
print("Ranking script:", ranking_script or "not found")
print("Report:", REPORT)
print("JSON:", JSON_OUTPUT)
