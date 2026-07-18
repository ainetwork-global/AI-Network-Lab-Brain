import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OPP = ROOT / "04_OPPORTUNITIES"
REPORT = ROOT / "12_REPORTS" / "LATEST_REVENUE_FUNNEL_DIAGNOSIS.md"

FILES = {
    "discovered": OPP / "GLOBAL_DISCOVERY_QUEUE.csv",
    "ranked_discovery": OPP / "DISCOVERY_INTELLIGENCE_QUEUE.csv",
    "promotion_decisions": OPP / "DISCOVERY_PROMOTION_DECISIONS.csv",
    "promoted": OPP / "DISCOVERY_PROMOTED_QUEUE.csv",
    "execution_queue": OPP / "GLOBAL_EXECUTION_QUEUE.csv",
    "verified": OPP / "verified_opportunities.csv",
    "economic_ranking": OPP / "execution_candidate_ranking.csv",
    "live_validation": OPP / "live_validated_opportunities.csv",
    "ready_queue": OPP / "EXECUTION_READY_QUEUE.csv",
}


def read_csv(path):
    if not path.exists():
        return []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        return list(csv.DictReader(file))


def clean(value):
    return str(value or "").strip()


def first(row, fields):
    for field in fields:
        value = clean(row.get(field))
        if value:
            return value
    return ""


def identity(row):
    organization = first(
        row,
        ["organization", "owner", "github_owner"],
    )

    repository = first(
        row,
        ["repository", "repository_name", "repo"],
    )

    if "/" in repository and not organization:
        organization, repository = repository.split("/", 1)

    issue = first(
        row,
        ["issue_number", "number", "issue"],
    )

    url = first(
        row,
        ["url", "issue_url", "source_url"],
    )

    if organization or repository or issue:
        return (
            organization.lower(),
            repository.lower(),
            issue,
        )

    return ("url", url.lower(), "")


data = {
    name: read_csv(path)
    for name, path in FILES.items()
}

stage_sets = {
    name: {identity(row) for row in rows}
    for name, rows in data.items()
}

promotion_reasons = Counter()

for row in data["promotion_decisions"]:
    status = clean(row.get("promotion_status"))

    if status != "PROMOTED":
        for reason in clean(
            row.get("promotion_reason")
        ).split(";"):
            if reason:
                promotion_reasons[reason] += 1

verification_statuses = Counter(
    first(
        row,
        [
            "verification_status",
            "status",
            "economic_status",
        ],
    )
    or "UNKNOWN"
    for row in data["verified"]
)

recommended_actions = Counter(
    first(
        row,
        [
            "recommended_action",
            "recommendation",
            "next_action",
        ],
    )
    or "UNKNOWN"
    for row in data["economic_ranking"]
)

live_statuses = Counter(
    first(
        row,
        [
            "live_validation_status",
            "validation_status",
            "status",
        ],
    )
    or "UNKNOWN"
    for row in data["live_validation"]
)

execution_statuses = Counter(
    first(
        row,
        [
            "execution_status",
            "status",
            "queue_status",
        ],
    )
    or "UNKNOWN"
    for row in data["ready_queue"]
)

promoted_ids = stage_sets["promoted"]
execution_ids = stage_sets["execution_queue"]
verified_ids = stage_sets["verified"]
ranking_ids = stage_sets["economic_ranking"]
live_ids = stage_sets["live_validation"]
ready_ids = stage_sets["ready_queue"]

lost_after_promotion = promoted_ids - execution_ids
lost_after_execution_queue = execution_ids - verified_ids
lost_after_verification = verified_ids - ranking_ids
lost_after_ranking = ranking_ids - live_ids
lost_after_live = live_ids - ready_ids

lines = [
    "# REVENUE FUNNEL DIAGNOSIS",
    "",
    f"Generated: {datetime.now(timezone.utc).isoformat()}",
    "",
    "## Stage Counts",
    "",
    "| Stage | Rows | Unique identities |",
    "|---|---:|---:|",
]

for name, rows in data.items():
    lines.append(
        f"| {name} | {len(rows)} | {len(stage_sets[name])} |"
    )

lines.extend([
    "",
    "## Drop-off Between Stages",
    "",
    "| Transition | Lost opportunities |",
    "|---|---:|",
    (
        "| Promoted → Execution Queue | "
        f"{len(lost_after_promotion)} |"
    ),
    (
        "| Execution Queue → Verified | "
        f"{len(lost_after_execution_queue)} |"
    ),
    (
        "| Verified → Economic Ranking | "
        f"{len(lost_after_verification)} |"
    ),
    (
        "| Economic Ranking → Live Validation | "
        f"{len(lost_after_ranking)} |"
    ),
    (
        "| Live Validation → Ready Queue | "
        f"{len(lost_after_live)} |"
    ),
    "",
    "## Promotion Rejection Reasons",
    "",
    "| Reason | Count |",
    "|---|---:|",
])

for reason, count in promotion_reasons.most_common():
    lines.append(f"| {reason} | {count} |")

lines.extend([
    "",
    "## Verification Statuses",
    "",
    "| Status | Count |",
    "|---|---:|",
])

for status, count in verification_statuses.most_common():
    lines.append(f"| {status} | {count} |")

lines.extend([
    "",
    "## Recommended Actions",
    "",
    "| Action | Count |",
    "|---|---:|",
])

for action, count in recommended_actions.most_common():
    lines.append(f"| {action} | {count} |")

lines.extend([
    "",
    "## Live Validation Statuses",
    "",
    "| Status | Count |",
    "|---|---:|",
])

for status, count in live_statuses.most_common():
    lines.append(f"| {status} | {count} |")

lines.extend([
    "",
    "## Execution Queue Statuses",
    "",
    "| Status | Count |",
    "|---|---:|",
])

for status, count in execution_statuses.most_common():
    lines.append(f"| {status} | {count} |")

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
print("REVENUE FUNNEL DIAGNOSIS")
print("=" * 72)

for name, rows in data.items():
    print(f"{name}: {len(rows)}")

print()
print("Drop-offs:")
print(
    "Promoted -> Execution Queue:",
    len(lost_after_promotion),
)
print(
    "Execution Queue -> Verified:",
    len(lost_after_execution_queue),
)
print(
    "Verified -> Ranking:",
    len(lost_after_verification),
)
print(
    "Ranking -> Live Validation:",
    len(lost_after_ranking),
)
print(
    "Live Validation -> Ready Queue:",
    len(lost_after_live),
)
print()
print("Report:", REPORT)
