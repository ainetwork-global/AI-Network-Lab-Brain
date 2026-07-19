from __future__ import annotations

import csv
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]

SOURCE_CSV = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "02_SOURCE_MAP"
    / "global_revenue_sources.csv"
)

RANKING_CSV = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "02_SOURCE_MAP"
    / "global_source_priority_ranking.csv"
)

BACKLOG_CSV = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "02_SOURCE_MAP"
    / "source_adapter_backlog.csv"
)

REPORT_FILE = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "12_REPORTS"
    / "LATEST_GLOBAL_REVENUE_SOURCE_MAP.md"
)

STATE_FILE = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "00_CURRENT_STATE"
    / "GLOBAL_REVENUE_SOURCE_MAP_STATE.md"
)


def yes(value: str) -> bool:
    return value.strip().lower() == "true"


def score(row: dict[str, str]) -> float:
    value = float(row.get("automation_priority", "0") or 0)

    if yes(row.get("canonical_payment_source", "")):
        value += 18

    if yes(row.get("explicit_executor_payment", "")):
        value += 18

    if yes(row.get("public_discovery", "")):
        value += 10

    if yes(row.get("global_access", "")):
        value += 8

    if row.get("api_available", "").lower() == "true":
        value += 12
    elif row.get("api_available", "").lower() == "partial":
        value += 6

    if yes(row.get("payment_crypto", "")):
        value += 4

    if yes(row.get("payment_fiat", "")):
        value += 4

    volume = row.get("expected_volume", "").lower()

    value += {
        "very_high": 15,
        "high": 12,
        "medium": 7,
        "low": 2,
    }.get(volume, 0)

    competition = row.get("competition_risk", "").lower()

    value -= {
        "very_high": 25,
        "high": 16,
        "medium": 8,
        "low": 0,
    }.get(competition, 5)

    status = row.get("adapter_status", "").upper()

    if status == "ACTIVE_PARTIAL":
        value += 8

    if row.get("verification_status", "").upper().startswith("NEEDS"):
        value -= 6

    return round(max(0, min(value, 200)), 2)


def health_check(url: str) -> tuple[str, str]:
    request = Request(
        url,
        headers={
            "User-Agent": "Global-Revenue-Brain/1.0",
        },
    )

    try:
        with urlopen(request, timeout=12) as response:
            return "REACHABLE", str(response.status)
    except Exception as exc:
        return "UNCONFIRMED", type(exc).__name__


def main() -> int:
    with SOURCE_CSV.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as handle:
        rows = list(csv.DictReader(handle))

    for row in rows:
        row["source_priority_score"] = score(row)

        health, detail = health_check(row["official_url"])
        row["live_health_status"] = health
        row["health_detail"] = detail
        row["last_checked_at"] = datetime.now(
            timezone.utc
        ).isoformat()

        if row["adapter_status"] == "NOT_BUILT":
            if (
                row["verification_status"] == "VERIFIED_OFFICIAL"
                and float(row["source_priority_score"]) >= 100
            ):
                next_action = "BUILD_ADAPTER_NOW"
            elif float(row["source_priority_score"]) >= 90:
                next_action = "VERIFY_THEN_BUILD"
            else:
                next_action = "BACKLOG"
        else:
            next_action = "IMPROVE_EXISTING_ADAPTER"

        row["next_action"] = next_action

    rows.sort(
        key=lambda row: float(row["source_priority_score"]),
        reverse=True,
    )

    fields: list[str] = []

    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)

    with RANKING_CSV.open(
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

    backlog = [
        row
        for row in rows
        if row["next_action"]
        in {
            "BUILD_ADAPTER_NOW",
            "VERIFY_THEN_BUILD",
            "IMPROVE_EXISTING_ADAPTER",
        }
    ]

    with BACKLOG_CSV.open(
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
        writer.writerows(backlog)

    lines = [
        "# Latest Global Revenue Source Map",
        "",
        f"- Generated: `{datetime.now(timezone.utc).isoformat()}`",
        f"- Sources mapped: **{len(rows)}**",
        f"- Reachable during check: "
        f"**{sum(1 for row in rows if row['live_health_status'] == 'REACHABLE')}**",
        f"- Adapter priorities: **{len(backlog)}**",
        "",
        "## Source priority ranking",
        "",
        "| Rank | Score | Source | Category | Health | Adapter | Next action |",
        "|---:|---:|---|---|---|---|---|",
    ]

    for index, row in enumerate(rows, 1):
        lines.append(
            f"| {index} | {row['source_priority_score']} | "
            f"{row['source_name']} | {row['category']} | "
            f"{row['live_health_status']} | "
            f"{row['adapter_status']} | {row['next_action']} |"
        )

    REPORT_FILE.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )

    top = backlog[:10]

    state_lines = [
        "# Global Revenue Source Map State",
        "",
        "Status: `GLOBAL_SOURCE_ROUTER_ACTIVE`",
        "",
        f"- Sources mapped: `{len(rows)}`",
        f"- Adapter candidates: `{len(backlog)}`",
        f"- Updated: `{datetime.now(timezone.utc).isoformat()}`",
        "",
        "## Next adapter priorities",
        "",
    ]

    for index, row in enumerate(top, 1):
        state_lines.append(
            f"{index}. `{row['source_name']}` — "
            f"{row['next_action']} — "
            f"score `{row['source_priority_score']}`"
        )

    state_lines.extend(
        [
            "",
            "## Operating rule",
            "",
            "Every new source must feed the existing canonical validation,",
            "payment confidence, competition, economic and execution gates.",
            "",
            "No adapter may submit applications, claims, proposals, reports,",
            "transactions or external commitments automatically.",
        ]
    )

    STATE_FILE.write_text(
        "\n".join(state_lines) + "\n",
        encoding="utf-8",
    )

    print("===== GLOBAL REVENUE SOURCE MAP =====")
    print(f"Sources mapped: {len(rows)}")
    print(
        "Reachable: "
        + str(
            sum(
                1
                for row in rows
                if row["live_health_status"] == "REACHABLE"
            )
        )
    )
    print(f"Adapter priorities: {len(backlog)}")
    print("")
    print("TOP ADAPTER PRIORITIES")

    for index, row in enumerate(top, 1):
        print(
            f"{index}. {row['source_name']} | "
            f"score={row['source_priority_score']} | "
            f"action={row['next_action']}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
