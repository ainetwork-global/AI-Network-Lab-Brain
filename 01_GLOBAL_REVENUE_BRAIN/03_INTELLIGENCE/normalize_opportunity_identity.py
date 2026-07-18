import argparse
import csv
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
OPPORTUNITIES = ROOT / "04_OPPORTUNITIES"
BACKUPS = (
    ROOT
    / "11_DATA"
    / "backups"
    / "identity_normalization"
)
REPORT = (
    ROOT
    / "12_REPORTS"
    / "LATEST_OPPORTUNITY_IDENTITY_NORMALIZATION.md"
)

FILES = [
    OPPORTUNITIES / "DISCOVERY_PROMOTED_QUEUE.csv",
    OPPORTUNITIES / "GLOBAL_EXECUTION_QUEUE.csv",
    OPPORTUNITIES / "verified_opportunities.csv",
    OPPORTUNITIES / "execution_candidate_ranking.csv",
    OPPORTUNITIES / "live_validated_opportunities.csv",
    OPPORTUNITIES / "EXECUTION_READY_QUEUE.csv",
]

CANONICAL_FIELDS = [
    "canonical_key",
    "organization",
    "repository_name",
    "issue_number",
    "source_url",
]


def clean(value):
    return str(value or "").strip()


def first(row, names):
    for name in names:
        value = clean(row.get(name))

        if value:
            return value

    return ""


def parse_github_url(value):
    value = clean(value)

    if not value:
        return "", "", ""

    try:
        parsed = urlparse(value)
    except Exception:
        return "", "", ""

    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if host not in {
        "github.com",
        "www.github.com",
        "api.github.com",
    }:
        return "", "", ""

    parts = [
        part
        for part in path.split("/")
        if part
    ]

    if host == "api.github.com":
        # /repos/owner/repository/issues/123
        if (
            len(parts) >= 5
            and parts[0].lower() == "repos"
        ):
            owner = parts[1]
            repository = parts[2]

            issue = ""

            if (
                parts[3].lower()
                in {"issues", "pulls"}
            ):
                issue = parts[4]

            return owner, repository, issue

        return "", "", ""

    # /owner/repository/issues/123
    if len(parts) < 2:
        return "", "", ""

    owner = parts[0]
    repository = parts[1]
    issue = ""

    if (
        len(parts) >= 4
        and parts[2].lower()
        in {"issues", "pull"}
    ):
        issue = parts[3]

    return owner, repository, issue


def parse_repository_value(value):
    value = clean(value).strip("/")

    if not value:
        return "", ""

    if value.startswith("http://") or value.startswith("https://"):
        owner, repository, _ = parse_github_url(value)
        return owner, repository

    if "/" not in value:
        return "", value

    owner, repository = value.split("/", 1)

    repository = repository.split("/", 1)[0]

    return owner, repository


def normalize_issue(value):
    value = clean(value)

    if not value:
        return ""

    match = re.search(r"\d+", value)

    if match:
        return match.group(0)

    return value


def canonical_identity(row):
    organization = first(
        row,
        [
            "organization",
            "owner",
            "github_owner",
            "org",
        ],
    )

    repository_name = first(
        row,
        [
            "repository_name",
            "repo",
        ],
    )

    repository_value = clean(
        row.get("repository")
    )

    issue_number = normalize_issue(
        first(
            row,
            [
                "issue_number",
                "number",
                "issue",
            ],
        )
    )

    source_url = first(
        row,
        [
            "source_url",
            "url",
            "issue_url",
            "html_url",
        ],
    )

    url_owner, url_repository, url_issue = (
        parse_github_url(source_url)
    )

    repo_owner, repo_name = parse_repository_value(
        repository_value
    )

    if not organization:
        organization = url_owner or repo_owner

    if not repository_name:
        repository_name = (
            url_repository
            or repo_name
            or (
                repository_value
                if "/" not in repository_value
                else ""
            )
        )

    if not issue_number:
        issue_number = normalize_issue(url_issue)

    organization = clean(organization)
    repository_name = clean(repository_name)
    issue_number = clean(issue_number)
    source_url = clean(source_url)

    if (
        organization
        and repository_name
        and issue_number
    ):
        canonical_key = (
            f"github:"
            f"{organization.lower()}/"
            f"{repository_name.lower()}#"
            f"{issue_number}"
        )

    elif source_url:
        canonical_key = (
            "url:"
            + source_url.lower().rstrip("/")
        )

    else:
        title = first(
            row,
            [
                "task_title",
                "title",
                "name",
            ],
        )

        canonical_key = (
            "title:"
            + re.sub(
                r"\s+",
                " ",
                title.lower(),
            ).strip()
        )

    return {
        "canonical_key": canonical_key,
        "organization": organization,
        "repository_name": repository_name,
        "issue_number": issue_number,
        "source_url": source_url,
    }


def read_csv(path):
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


def write_csv(path, fields, rows):
    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fields,
            extrasaction="ignore",
        )

        writer.writeheader()
        writer.writerows(rows)


parser = argparse.ArgumentParser()

parser.add_argument(
    "--dry-run",
    action="store_true",
)

args = parser.parse_args()

BACKUPS.mkdir(
    parents=True,
    exist_ok=True,
)

results = []

for path in FILES:
    if not path.exists():
        results.append({
            "file": path.name,
            "status": "NOT_FOUND",
            "rows": 0,
            "github_identity": 0,
            "url_identity": 0,
            "title_identity": 0,
            "changed_rows": 0,
        })

        continue

    fields, rows = read_csv(path)

    output_fields = list(fields)

    for field in CANONICAL_FIELDS:
        if field not in output_fields:
            output_fields.append(field)

    changed_rows = 0
    github_identity = 0
    url_identity = 0
    title_identity = 0

    for row in rows:
        before = {
            field: clean(row.get(field))
            for field in CANONICAL_FIELDS
        }

        identity = canonical_identity(row)

        for field, value in identity.items():
            if value:
                row[field] = value
            elif field not in row:
                row[field] = ""

        # Mantém compatibilidade com arquivos que usam repository.
        if (
            "repository" in output_fields
            and identity["repository_name"]
        ):
            existing_repository = clean(
                row.get("repository")
            )

            if (
                not existing_repository
                and identity["organization"]
            ):
                row["repository"] = (
                    identity["organization"]
                    + "/"
                    + identity["repository_name"]
                )

        after = {
            field: clean(row.get(field))
            for field in CANONICAL_FIELDS
        }

        if before != after:
            changed_rows += 1

        canonical_key = identity["canonical_key"]

        if canonical_key.startswith("github:"):
            github_identity += 1
        elif canonical_key.startswith("url:"):
            url_identity += 1
        else:
            title_identity += 1

    if not args.dry_run:
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

        backup = (
            BACKUPS
            / f"{path.stem}_{timestamp}.csv"
        )

        shutil.copy2(path, backup)

        write_csv(
            path,
            output_fields,
            rows,
        )

        status = "UPDATED"
    else:
        status = "DRY_RUN"

    results.append({
        "file": path.name,
        "status": status,
        "rows": len(rows),
        "github_identity": github_identity,
        "url_identity": url_identity,
        "title_identity": title_identity,
        "changed_rows": changed_rows,
    })


report_lines = [
    "# OPPORTUNITY IDENTITY NORMALIZATION",
    "",
    (
        "Generated: "
        + datetime.now(timezone.utc).isoformat()
    ),
    "",
    "## Summary",
    "",
    "| File | Status | Rows | Changed | GitHub identity | URL identity | Title fallback |",
    "|---|---|---:|---:|---:|---:|---:|",
]

for result in results:
    report_lines.append(
        f"| {result['file']} | "
        f"{result['status']} | "
        f"{result['rows']} | "
        f"{result['changed_rows']} | "
        f"{result['github_identity']} | "
        f"{result['url_identity']} | "
        f"{result['title_identity']} |"
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
print("OPPORTUNITY IDENTITY NORMALIZATION")
print("=" * 72)

for result in results:
    print()
    print("File:", result["file"])
    print("Status:", result["status"])
    print("Rows:", result["rows"])
    print("Changed:", result["changed_rows"])
    print(
        "GitHub identities:",
        result["github_identity"],
    )
    print(
        "URL identities:",
        result["url_identity"],
    )
    print(
        "Title fallbacks:",
        result["title_identity"],
    )

print()
print("Report:", REPORT)
