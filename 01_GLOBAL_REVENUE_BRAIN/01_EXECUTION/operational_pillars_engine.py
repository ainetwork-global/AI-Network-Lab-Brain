from __future__ import annotations

import csv
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from autonomy_risk_policy import assess

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"
QUEUE = ROOT / "04_OPPORTUNITIES" / "GLOBAL_DECISION_QUEUE.csv"
APPROVAL_CSV = ROOT / "04_OPPORTUNITIES" / "HUMAN_APPROVAL_QUEUE.csv"
OPERATIONS_CSV = ROOT / "04_OPPORTUNITIES" / "REVENUE_OPERATIONS.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_OPERATIONAL_PILLARS.md"
WORKSPACES = ROOT / "08_WORKSPACES"
SETTLEMENT_CONFIG = ROOT / "01_CONFIG" / "settlement_profiles.json"


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: object) -> str:
    return str(value or "").strip()


def number(value: object) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def key_for(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def initialize(db: sqlite3.Connection) -> None:
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS revenue_operations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_key TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            source_url TEXT NOT NULL,
            reward_amount REAL NOT NULL DEFAULT 0,
            reward_currency TEXT,
            truth_status TEXT NOT NULL,
            development_status TEXT NOT NULL DEFAULT 'not_started',
            claim_status TEXT NOT NULL DEFAULT 'not_requested',
            submission_status TEXT NOT NULL DEFAULT 'not_prepared',
            review_status TEXT NOT NULL DEFAULT 'not_submitted',
            payment_status TEXT NOT NULL DEFAULT 'not_expected',
            settlement_status TEXT NOT NULL DEFAULT 'not_configured',
            workspace_path TEXT,
            claim_reference TEXT,
            submission_reference TEXT,
            payment_reference TEXT,
            last_checked_at TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS human_approval_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_key TEXT NOT NULL,
            operation_id INTEGER NOT NULL,
            action_type TEXT NOT NULL,
            action_summary TEXT NOT NULL,
            external_target TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            requested_at TEXT NOT NULL,
            decided_at TEXT,
            decision_reference TEXT,
            UNIQUE(candidate_key, action_type, status)
        );

        CREATE TABLE IF NOT EXISTS operational_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            candidate_key TEXT NOT NULL,
            pillar TEXT NOT NULL,
            event_type TEXT NOT NULL,
            event_status TEXT NOT NULL,
            external_action INTEGER NOT NULL DEFAULT 0,
            details TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS settlement_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_key TEXT NOT NULL UNIQUE,
            provider TEXT NOT NULL,
            rail TEXT NOT NULL,
            currency TEXT,
            country TEXT NOT NULL DEFAULT 'BR',
            verified INTEGER NOT NULL DEFAULT 0,
            receive_enabled INTEGER NOT NULL DEFAULT 0,
            movement_enabled INTEGER NOT NULL DEFAULT 0,
            sensitive_data_location TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )
    columns = {
        row[1] for row in db.execute("PRAGMA table_info(revenue_operations)")
    }
    for name, definition in {
        "risk_level": "TEXT NOT NULL DEFAULT 'UNASSESSED'",
        "risk_decision": "TEXT NOT NULL DEFAULT 'HUMAN_APPROVAL_REQUIRED'",
        "risk_reasons_json": "TEXT NOT NULL DEFAULT '[]'",
        "executor_attempts": "INTEGER NOT NULL DEFAULT 0",
        "next_retry_at": "TEXT",
        "last_executor_error": "TEXT",
    }.items():
        if name not in columns:
            db.execute(f"ALTER TABLE revenue_operations ADD COLUMN {name} {definition}")

    columns = {
        row[1] for row in db.execute("PRAGMA table_info(settlement_profiles)")
    }
    if "verification_status" not in columns:
        db.execute(
            "ALTER TABLE settlement_profiles ADD COLUMN verification_status TEXT NOT NULL DEFAULT 'pending'"
        )

    if SETTLEMENT_CONFIG.exists():
        config = json.loads(SETTLEMENT_CONFIG.read_text(encoding="utf-8-sig"))
        for profile in config.get("profiles", []):
            timestamp = now()
            db.execute(
                """
                INSERT INTO settlement_profiles (
                    profile_key, provider, rail, currency, country,
                    verified, receive_enabled, movement_enabled,
                    sensitive_data_location, verification_status,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, 0, 0, 0, NULL, ?, ?, ?)
                ON CONFLICT(profile_key) DO UPDATE SET
                    provider = excluded.provider,
                    rail = excluded.rail,
                    currency = excluded.currency,
                    country = excluded.country,
                    verification_status = excluded.verification_status,
                    updated_at = excluded.updated_at
                """,
                (
                    profile["profile_key"],
                    profile["provider"],
                    profile["rail"],
                    profile.get("currency"),
                    profile.get("country", "BR"),
                    profile.get("verification_status", "pending"),
                    timestamp,
                    timestamp,
                ),
            )
    db.commit()


def event(db: sqlite3.Connection, candidate_key: str, pillar: str, kind: str, status: str, details: str) -> None:
    db.execute(
        """
        INSERT INTO operational_events
        (candidate_key, pillar, event_type, event_status, external_action, details, created_at)
        VALUES (?, ?, ?, ?, 0, ?, ?)
        """,
        (candidate_key, pillar, kind, status, details, now()),
    )


def request_approval(
    db: sqlite3.Connection,
    operation_id: int,
    candidate_key: str,
    action_type: str,
    summary: str,
    target: str,
) -> None:
    existing = db.execute(
        """
        SELECT id FROM human_approval_requests
        WHERE candidate_key = ? AND action_type = ? AND status = 'pending'
        """,
        (candidate_key, action_type),
    ).fetchone()
    if existing:
        return
    db.execute(
        """
        INSERT INTO human_approval_requests
        (candidate_key, operation_id, action_type, action_summary, external_target, status, requested_at)
        VALUES (?, ?, ?, ?, ?, 'pending', ?)
        """,
        (candidate_key, operation_id, action_type, summary, target, now()),
    )


def prepare_workspace(row: dict[str, str], candidate_key: str) -> str:
    directory = WORKSPACES / candidate_key[:12]
    directory.mkdir(parents=True, exist_ok=True)
    packet = directory / "EXECUTION_PACKET.md"
    packet.write_text(
        "\n".join(
            [
                "# Execution Packet",
                "",
                f"Title: {clean(row.get('title'))}",
                f"Source: {clean(row.get('url'))}",
                f"Reward: {clean(row.get('reward_currency'))} {clean(row.get('reward_amount'))}",
                f"Truth status: {clean(row.get('truth_status'))}",
                "",
                "## Automated development boundary",
                "",
                "- Work only inside this isolated workspace.",
                "- Use only free/already-authorized tools.",
                "- Do not comment, claim, apply, publish, open a PR, accept terms, sign a wallet, or spend funds.",
                "- Produce implementation, tests, evidence, and a submission draft before requesting approval.",
                "",
                "## Required outputs",
                "",
                "- REQUIREMENTS.md",
                "- IMPLEMENTATION_PLAN.md",
                "- deliverable/",
                "- TEST_EVIDENCE.md",
                "- SUBMISSION_DRAFT.md",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return str(packet.relative_to(ROOT))


def main() -> int:
    rows: list[dict[str, str]] = []
    if QUEUE.exists():
        with QUEUE.open(encoding="utf-8-sig", newline="") as handle:
            rows = list(csv.DictReader(handle))

    with sqlite3.connect(DB) as db:
        db.row_factory = sqlite3.Row
        initialize(db)

        # Reconcile every tracked operation with the latest truth gate.  A stale
        # approval must never survive when an opportunity closes, becomes
        # unfunded, or is identified as a false positive.
        latest = {
            key_for(clean(row.get("url"))): clean(row.get("truth_status"))
            for row in rows if clean(row.get("url"))
        }
        tracked = db.execute(
            "SELECT id, candidate_key, truth_status FROM revenue_operations"
        ).fetchall()
        for operation in tracked:
            current = latest.get(operation["candidate_key"], "REMOVED_FROM_LIVE_QUEUE")
            if current != operation["truth_status"]:
                db.execute(
                    "UPDATE revenue_operations SET truth_status = ?, updated_at = ?, last_checked_at = ? WHERE id = ?",
                    (current, now(), now(), operation["id"]),
                )
            if current != "READY_FOR_TECHNICAL_REVIEW":
                db.execute(
                    """
                    UPDATE human_approval_requests
                    SET status = 'cancelled_by_truth_gate', decided_at = ?,
                        decision_reference = ?
                    WHERE operation_id = ? AND status = 'pending'
                    """,
                    (now(), current, operation["id"]),
                )

        for row in rows:
            status = clean(row.get("truth_status"))
            if status != "READY_FOR_TECHNICAL_REVIEW":
                continue
            url = clean(row.get("url"))
            candidate_key = key_for(url)
            timestamp = now()
            db.execute(
                """
                INSERT INTO revenue_operations (
                    candidate_key, title, source_url, reward_amount, reward_currency,
                    truth_status, last_checked_at, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(candidate_key) DO UPDATE SET
                    title = excluded.title,
                    reward_amount = excluded.reward_amount,
                    reward_currency = excluded.reward_currency,
                    truth_status = excluded.truth_status,
                    last_checked_at = excluded.last_checked_at,
                    updated_at = excluded.updated_at
                """,
                (
                    candidate_key,
                    clean(row.get("title")),
                    url,
                    number(row.get("reward_amount")),
                    clean(row.get("reward_currency")),
                    status,
                    timestamp,
                    timestamp,
                    timestamp,
                ),
            )
            operation = db.execute(
                "SELECT * FROM revenue_operations WHERE candidate_key = ?",
                (candidate_key,),
            ).fetchone()

            risk = assess(row)
            db.execute(
                """
                UPDATE revenue_operations
                SET risk_level = ?, risk_decision = ?, risk_reasons_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (risk.level, risk.decision, json.dumps(risk.reasons), now(), operation["id"]),
            )

            if risk.decision == "REJECT":
                db.execute(
                    "UPDATE revenue_operations SET development_status = 'risk_rejected', updated_at = ? WHERE id = ?",
                    (now(), operation["id"]),
                )
                event(db, candidate_key, "risk", "prohibited_opportunity_rejected", "blocked", ", ".join(risk.reasons))
                continue

            if risk.decision == "HUMAN_APPROVAL_REQUIRED":
                db.execute(
                    "UPDATE revenue_operations SET development_status = 'risk_blocked', updated_at = ? WHERE id = ?",
                    (now(), operation["id"]),
                )
                request_approval(
                    db,
                    operation["id"],
                    candidate_key,
                    "risk_review",
                    "Risco detectado: " + ", ".join(risk.reasons),
                    url,
                )
                event(db, candidate_key, "risk", "human_approval_requested", "blocked", ", ".join(risk.reasons))
                continue

            if operation["development_status"] == "not_started":
                workspace = prepare_workspace(row, candidate_key)
                db.execute(
                    """
                    UPDATE revenue_operations
                    SET development_status = 'workspace_prepared',
                        workspace_path = ?, updated_at = ?
                    WHERE id = ?
                    """,
                    (workspace, now(), operation["id"]),
                )
                event(db, candidate_key, "development", "workspace_prepared", "success", workspace)
                # Internal analysis, implementation and tests are reversible and
                # do not touch the target platform. They can proceed automatically.
                db.execute(
                    """
                    UPDATE revenue_operations
                    SET development_status = 'ready_for_autonomous_executor',
                        updated_at = ? WHERE id = ?
                    """,
                    (now(), operation["id"]),
                )
                event(
                    db, candidate_key, "development", "queued_for_executor",
                    "success", "Internal development authorized; external actions remain gated."
                )

        db.commit()

        operations = db.execute(
            "SELECT * FROM revenue_operations ORDER BY reward_amount DESC, id"
        ).fetchall()
        approvals = db.execute(
            """
            SELECT a.*, o.title, o.reward_amount, o.reward_currency
            FROM human_approval_requests a
            JOIN revenue_operations o ON o.id = a.operation_id
            WHERE a.status = 'pending'
            ORDER BY a.requested_at
            """
        ).fetchall()
        settlements = db.execute(
            "SELECT * FROM settlement_profiles ORDER BY provider, rail"
        ).fetchall()

    APPROVAL_CSV.parent.mkdir(parents=True, exist_ok=True)
    approval_fields = [
        "approval_id", "action_type", "title", "reward_amount", "reward_currency",
        "external_target", "action_summary", "status", "requested_at",
    ]
    with APPROVAL_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=approval_fields)
        writer.writeheader()
        for row in approvals:
            writer.writerow(
                {
                    "approval_id": row["id"],
                    "action_type": row["action_type"],
                    "title": row["title"],
                    "reward_amount": row["reward_amount"],
                    "reward_currency": row["reward_currency"],
                    "external_target": row["external_target"],
                    "action_summary": row["action_summary"],
                    "status": row["status"],
                    "requested_at": row["requested_at"],
                }
            )

    operation_fields = [
        "id", "title", "source_url", "reward_amount", "reward_currency",
        "truth_status", "development_status", "claim_status", "submission_status",
        "review_status", "payment_status", "settlement_status", "workspace_path",
        "last_checked_at", "risk_level", "risk_decision", "risk_reasons_json",
        "executor_attempts", "next_retry_at", "last_executor_error",
    ]
    with OPERATIONS_CSV.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=operation_fields)
        writer.writeheader()
        for row in operations:
            writer.writerow({field: row[field] for field in operation_fields})

    lines = [
        "# OPERATIONAL REVENUE PILLARS",
        "",
        f"Generated: `{now()}`",
        "",
        f"- Operations tracked: **{len(operations)}**",
        f"- Pending individual approvals: **{len(approvals)}**",
        f"- Settlement profiles configured: **{len(settlements)}**",
        f"- Operations waiting for retry: **{sum(bool(row['next_retry_at']) for row in operations)}**",
        "",
        "## Pillar status",
        "",
        "- Development: isolated workspace is automatically queued for the autonomous executor; no human approval is required for internal code and tests.",
        "- Claim/application: individual approval queue enabled; no automatic external claim.",
        "- Submission: state tracking enabled; external submission requires individual approval.",
        "- Review/payment monitoring: persistent operational state enabled.",
        "- Receive/move funds: evidence ledger supported; no settlement profile or movement is enabled by default.",
        "",
        "No external action, contract, publication, wallet signature, claim, submission, payment, withdrawal, or transfer was performed.",
        "",
        "## Pending approvals",
        "",
    ]
    for row in approvals:
        lines += [
            f"### Approval {row['id']} — {row['action_type']}",
            "",
            f"- Title: {row['title']}",
            f"- Reward: {row['reward_currency']} {row['reward_amount']}",
            f"- Action: {row['action_summary']}",
            f"- Target: {row['external_target']}",
            "",
        ]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Operations={len(operations)} approvals={len(approvals)} settlements={len(settlements)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
