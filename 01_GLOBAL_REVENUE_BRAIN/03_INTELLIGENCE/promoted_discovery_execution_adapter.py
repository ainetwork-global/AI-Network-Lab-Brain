import argparse
import csv
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

INPUT = (
    ROOT
    / "04_OPPORTUNITIES"
    / "DISCOVERY_PROMOTED_QUEUE.csv"
)

TARGET = (
    ROOT
    / "04_OPPORTUNITIES"
    / "GLOBAL_EXECUTION_QUEUE.csv"
)

REPORT = (
    ROOT
    / "12_REPORTS"
    / "LATEST_PROMOTED_DISCOVERY_INTEGRATION.md"
)


def clean(value):
    return str(value or "").strip()


def number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def read_csv(path):
    if not path.exists():
        return [], []

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        return (
            list(reader.fieldnames or []),
            list(reader),
        )


def repository_parts(value):
    value = clean(value).strip("/")

    if "/" not in value:
        return "", value

    owner, repository = value.split("/", 1)

    return owner, repository


def existing_identity(row):
    organization = clean(
        row.get("organization")
        or row.get("owner")
        or row.get("github_owner")
    )

    repository = clean(
        row.get("repository")
        or row.get("repository_name")
        or row.get("repo")
    )

    if "/" in repository and not organization:
        organization, repository = repository_parts(
            repository
        )

    issue_number = clean(
        row.get("issue_number")
        or row.get("number")
        or row.get("issue")
    )

    url = clean(
        row.get("url")
        or row.get("issue_url")
        or row.get("source_url")
    ).lower()

    if organization or repository or issue_number:
        return (
            organization.lower(),
            repository.lower(),
            issue_number,
        )

    return ("url", url, "")


def set_first_available(
    row,
    fields,
    candidates,
    value,
):
    for field in candidates:
        if field in fields:
            row[field] = value
            return True

    return False


parser = argparse.ArgumentParser()

parser.add_argument(
    "--max-candidates",
    type=int,
    default=50,
)

parser.add_argument(
    "--min-promotion-score",
    type=float,
    default=60.0,
)

args = parser.parse_args()

if not INPUT.exists():
    raise SystemExit(
        f"Fila promovida não encontrada: {INPUT}"
    )

source_fields, source_rows = read_csv(INPUT)
target_fields, target_rows = read_csv(TARGET)

if not target_fields:
    target_fields = [
        "source",
        "organization",
        "repository",
        "issue_number",
        "title",
        "url",
        "execution_status",
        "discovery_score",
        "promotion_score",
        "promotion_status",
        "promotion_reason",
        "discovered_at",
    ]

required_metadata = [
    "discovery_score",
    "promotion_score",
    "promotion_status",
    "promotion_reason",
]

for field in required_metadata:
    if field not in target_fields:
        target_fields.append(field)

eligible = []

for row in source_rows:
    if clean(row.get("promotion_status")) != "PROMOTED":
        continue

    promotion_score = number(
        row.get("promotion_score")
    )

    if promotion_score < args.min_promotion_score:
        continue

    eligible.append(row)

eligible.sort(
    key=lambda row: (
        number(row.get("promotion_score")),
        number(row.get("discovery_score")),
    ),
    reverse=True,
)

eligible = eligible[:args.max_candidates]

existing_keys = {
    existing_identity(row)
    for row in target_rows
}

added_rows = []
duplicate_count = 0

for source in eligible:
    full_repository = clean(
        source.get("repository")
    )

    organization, repository = repository_parts(
        full_repository
    )

    issue_number = clean(
        source.get("issue_number")
    )

    url = clean(
        source.get("url")
    )

    identity = (
        organization.lower(),
        repository.lower(),
        issue_number,
    )

    if identity in existing_keys:
        duplicate_count += 1
        continue

    output = {
        field: ""
        for field in target_fields
    }

    set_first_available(
        output,
        target_fields,
        ["source", "source_name", "origin"],
        "global_discovery_hub",
    )

    set_first_available(
        output,
        target_fields,
        ["organization", "owner", "github_owner"],
        organization,
    )

    set_first_available(
        output,
        target_fields,
        ["repository_name", "repo"],
        repository,
    )

    if "repository" in target_fields:
        if (
            "organization" in target_fields
            or "owner" in target_fields
            or "github_owner" in target_fields
        ):
            output["repository"] = repository
        else:
            output["repository"] = full_repository

    set_first_available(
        output,
        target_fields,
        ["issue_number", "number", "issue"],
        issue_number,
    )

    set_first_available(
        output,
        target_fields,
        ["title", "opportunity_title", "name"],
        clean(source.get("title")),
    )

    set_first_available(
        output,
        target_fields,
        ["url", "issue_url", "source_url"],
        url,
    )

    set_first_available(
        output,
        target_fields,
        [
            "execution_status",
            "status",
            "queue_status",
        ],
        "DISCOVERED",
    )

    set_first_available(
        output,
        target_fields,
        ["description", "body", "summary"],
        clean(source.get("title")),
    )

    output["discovery_score"] = clean(
        source.get("discovery_score")
    )

    output["promotion_score"] = clean(
        source.get("promotion_score")
    )

    output["promotion_status"] = clean(
        source.get("promotion_status")
    )

    output["promotion_reason"] = clean(
        source.get("promotion_reason")
    )

    if "discovered_at" in target_fields:
        output["discovered_at"] = (
            datetime.now(timezone.utc).isoformat()
        )

    added_rows.append(output)
    target_rows.append(output)
    existing_keys.add(identity)

TARGET.parent.mkdir(
    parents=True,
    exist_ok=True,
)

backup_path = None

if TARGET.exists():
    backup_directory = (
        ROOT
        / "11_DATA"
        / "backups"
        / "execution_queues"
    )

    backup_directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    backup_path = (
        backup_directory
        / (
            "GLOBAL_EXECUTION_QUEUE_"
            + datetime.now().strftime("%Y%m%d_%H%M%S")
            + ".csv"
        )
    )

    shutil.copy2(TARGET, backup_path)

with TARGET.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=target_fields,
        extrasaction="ignore",
    )

    writer.writeheader()
    writer.writerows(target_rows)

report_lines = [
    "# PROMOTED DISCOVERY INTEGRATION",
    "",
    (
        "Generated: "
        + datetime.now(timezone.utc).isoformat()
    ),
    "",
    "## Summary",
    "",
    f"- Promoted rows available: {len(source_rows)}",
    (
        "- Eligible after minimum score: "
        f"{len(eligible)}"
    ),
    f"- Added to execution queue: {len(added_rows)}",
    f"- Duplicates skipped: {duplicate_count}",
    (
        "- Total execution queue rows: "
        f"{len(target_rows)}"
    ),
    (
        "- Minimum promotion score: "
        f"{args.min_promotion_score}"
    ),
    (
        "- Maximum candidates this run: "
        f"{args.max_candidates}"
    ),
    (
        "- Backup: "
        + (
            str(backup_path)
            if backup_path
            else "not required"
        )
    ),
    "",
    "## Added Opportunities",
    "",
    (
        "| Rank | Organization | Repository | "
        "Issue | Promotion Score | Title |"
    ),
    "|---:|---|---|---:|---:|---|",
]

for index, row in enumerate(
    added_rows,
    start=1,
):
    title = clean(
        row.get("title")
        or row.get("opportunity_title")
        or row.get("name")
    ).replace("|", "/").replace("\n", " ")

    report_lines.append(
        f"| {index} | "
        f"{clean(row.get('organization'))} | "
        f"{clean(row.get('repository'))} | "
        f"{clean(row.get('issue_number'))} | "
        f"{clean(row.get('promotion_score'))} | "
        f"{title} |"
    )

REPORT.parent.mkdir(
    parents=True,
    exist_ok=True,
)

REPORT.write_text(
    "\n".join(report_lines) + "\n",
    encoding="utf-8",
)

print()
print("=" * 72)
print("PROMOTED DISCOVERY EXECUTION ADAPTER")
print("=" * 72)
print("Eligible:", len(eligible))
print("Added:", len(added_rows))
print("Duplicates:", duplicate_count)
print("Execution queue total:", len(target_rows))
print("Target:", TARGET)
print("Backup:", backup_path or "not required")
print("Report:", REPORT)
