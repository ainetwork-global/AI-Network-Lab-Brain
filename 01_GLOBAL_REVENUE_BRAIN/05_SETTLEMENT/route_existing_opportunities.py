from __future__ import annotations

import hashlib
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_OPPORTUNITY_SETTLEMENT_ROUTES.md"


SOURCE_TABLES = (
    "devpost_execution_queue",
    "official_source_candidates",
    "algora_open_bounties",
    "opportunity_verifications",
    "revenue_execution_queue",
)

TITLE_COLUMNS = (
    "title",
    "name",
    "opportunity_title",
)

URL_COLUMNS = (
    "url",
    "github_url",
    "algora_url",
    "source_url",
)

AMOUNT_COLUMNS = (
    "reward_amount",
    "reward",
    "total_prize_usd",
    "expected_reward",
    "expected_value",
    "amount",
)

CURRENCY_COLUMNS = (
    "reward_currency",
    "currency",
)

STATUS_COLUMNS = (
    "api_truth_status",
    "triage_status",
    "validation_status",
    "status",
    "verification_status",
)

SOURCE_COLUMNS = (
    "source_name",
    "source",
    "organization",
    "provider",
)

TEXT_COLUMNS = (
    "title",
    "name",
    "description",
    "reason",
    "skills",
    "category",
    "source_name",
    "source",
    "organization",
    "url",
)

ELIGIBLE_STATUS_TERMS = (
    "actionable",
    "approved",
    "priority_review",
    "standard_review",
    "verified",
    "open",
)

CRYPTO_TERMS = (
    "usdc",
    "base",
    "onchain",
    "on-chain",
    "x402",
    "crypto bounty",
    "stablecoin",
    "wallet payment",
)

BANK_TERMS = (
    "bank transfer",
    "wire transfer",
    "ach",
    "direct deposit",
    "usd transfer",
)

STRIPE_TERMS = (
    "stripe",
    "subscription",
    "saas",
    "checkout",
    "credit package",
    "commercial payment",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def table_exists(
    conn: sqlite3.Connection,
    table: str,
) -> bool:
    return bool(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type='table' AND name=?
            """,
            (table,),
        ).fetchone()[0]
    )


def table_columns(
    conn: sqlite3.Connection,
    table: str,
) -> list[str]:
    return [
        row[1]
        for row in conn.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()
    ]


def first_value(
    row: sqlite3.Row,
    candidates: tuple[str, ...],
) -> Any:
    keys = set(row.keys())

    for name in candidates:
        if name in keys and row[name] not in (None, ""):
            return row[name]

    return None


def normalized_text(row: sqlite3.Row) -> str:
    keys = set(row.keys())
    values = []

    for column in TEXT_COLUMNS:
        if column in keys and row[column] not in (None, ""):
            values.append(str(row[column]))

    return " ".join(values).lower()


def opportunity_key(
    table: str,
    row_id: Any,
    title: str,
    url: str,
) -> str:
    raw = f"{table}|{row_id}|{title}|{url}"

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def status_is_eligible(status: str) -> bool:
    lowered = status.lower()

    return any(
        term in lowered
        for term in ELIGIBLE_STATUS_TERMS
    )


def infer_route(
    text: str,
    currency: str,
) -> tuple[str | None, str, str, str]:
    currency_upper = (currency or "").upper()

    if (
        currency_upper == "USDC"
        or any(term in text for term in CRYPTO_TERMS)
    ):
        return (
            "base_usdc_wallet",
            "wallet",
            currency_upper or "USDC",
            "candidate",
        )

    if any(term in text for term in BANK_TERMS):
        return (
            "nomad_usd",
            "bank_transfer",
            currency_upper or "USD",
            "candidate",
        )

    if any(term in text for term in STRIPE_TERMS):
        return (
            "stripe_commercial",
            "stripe",
            currency_upper or "USD",
            "candidate",
        )

    return (
        None,
        "unknown",
        currency_upper or "UNKNOWN",
        "review_required",
    )


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

required_tables = (
    "settlement_targets",
    "opportunity_settlement_routes",
)

for table in required_tables:
    if not table_exists(conn, table):
        raise RuntimeError(
            f"Tabela obrigatória ausente: {table}"
        )

available_sources = [
    table
    for table in SOURCE_TABLES
    if table_exists(conn, table)
]

print()
print("===== SETTLEMENT ROUTING =====")
print("Source tables:", len(available_sources))

processed = 0
routed = 0
review_required = 0
skipped_status = 0
routes_by_target: dict[str, int] = {}

for table in available_sources:
    columns = table_columns(conn, table)

    if "id" not in columns:
        continue

    rows = conn.execute(
        f'SELECT * FROM "{table}"'
    ).fetchall()

    for row in rows:
        processed += 1

        title = str(
            first_value(row, TITLE_COLUMNS)
            or f"{table} record {row['id']}"
        )

        url = str(
            first_value(row, URL_COLUMNS)
            or ""
        )

        amount_raw = first_value(
            row,
            AMOUNT_COLUMNS,
        )

        try:
            expected_amount = (
                float(amount_raw)
                if amount_raw not in (None, "")
                else None
            )
        except (TypeError, ValueError):
            expected_amount = None

        currency = str(
            first_value(row, CURRENCY_COLUMNS)
            or ""
        )

        status = str(
            first_value(row, STATUS_COLUMNS)
            or ""
        )

        if status and not status_is_eligible(status):
            skipped_status += 1
            continue

        source = str(
            first_value(row, SOURCE_COLUMNS)
            or table
        )

        text = normalized_text(row)

        target_key, payment_method, route_currency, route_status = (
            infer_route(text, currency)
        )

        key = opportunity_key(
            table,
            row["id"],
            title,
            url,
        )

        evidence = (
            f"source_table={table}; "
            f"source={source}; "
            f"status={status or 'not_available'}; "
            f"title={title}; "
            f"url={url or 'not_available'}"
        )

        if target_key is None:
            review_required += 1
            continue

        conn.execute(
            """
            INSERT INTO opportunity_settlement_routes (
                opportunity_key,
                settlement_target_key,
                payment_method,
                currency,
                expected_amount,
                minimum_amount,
                payment_instructions_status,
                route_status,
                human_approval_required,
                evidence,
                created_at,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, NULL,
                'not_verified',
                ?,
                1,
                ?,
                ?,
                ?
            )
            ON CONFLICT(
                opportunity_key,
                settlement_target_key
            )
            DO UPDATE SET
                payment_method =
                    excluded.payment_method,
                currency =
                    excluded.currency,
                expected_amount =
                    excluded.expected_amount,
                payment_instructions_status =
                    'not_verified',
                route_status =
                    excluded.route_status,
                human_approval_required = 1,
                evidence =
                    excluded.evidence,
                updated_at =
                    excluded.updated_at
            """,
            (
                key,
                target_key,
                payment_method,
                route_currency,
                expected_amount,
                route_status,
                evidence,
                utc_now(),
                utc_now(),
            ),
        )

        routed += 1
        routes_by_target[target_key] = (
            routes_by_target.get(target_key, 0)
            + 1
        )

conn.commit()

rows = conn.execute(
    """
    SELECT
        r.settlement_target_key,
        t.display_name,
        r.payment_method,
        r.currency,
        r.expected_amount,
        r.route_status,
        r.payment_instructions_status,
        r.evidence
    FROM opportunity_settlement_routes r
    JOIN settlement_targets t
      ON t.target_key = r.settlement_target_key
    ORDER BY
        CASE r.route_status
            WHEN 'candidate' THEN 1
            ELSE 2
        END,
        COALESCE(r.expected_amount, 0) DESC
    """
).fetchall()

lines = [
    "# Global Revenue Brain — Opportunity Settlement Routes",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "Nenhum pagamento foi solicitado ou movimentado.",
    "Nenhum dado sensível foi gravado.",
    "",
    "## Resumo",
    "",
    f"- Registros analisados: **{processed}**",
    f"- Rotas candidatas criadas: **{routed}**",
    f"- Método de pagamento não identificado: **{review_required}**",
    f"- Registros ignorados por status: **{skipped_status}**",
    "",
    "## Rotas por destino",
    "",
]

for target_key, total in sorted(
    routes_by_target.items()
):
    lines.append(
        f"- `{target_key}`: **{total}**"
    )

lines.extend([
    "",
    "## Rotas",
    "",
])

for index, row in enumerate(rows, 1):
    lines.extend([
        f"### {index}. {row['display_name']}",
        "",
        f"- Método: {row['payment_method']}",
        f"- Moeda: {row['currency']}",
        f"- Valor esperado: "
        f"{row['expected_amount'] if row['expected_amount'] is not None else 'não identificado'}",
        f"- Status da rota: **{row['route_status']}**",
        f"- Instruções de pagamento: "
        f"**{row['payment_instructions_status']}**",
        "- Aprovação humana obrigatória: sim",
        f"- Evidência: {row['evidence']}",
        "",
    ])

REPORT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print("Records analyzed:", processed)
print("Routes created:", routed)
print("Payment method review required:", review_required)
print("Skipped by status:", skipped_status)

print()
print("===== ROUTES BY TARGET =====")

if routes_by_target:
    for target_key, total in sorted(
        routes_by_target.items()
    ):
        print(f"{target_key}: {total}")
else:
    print("No supported settlement routes identified.")

print()
print("===== TOP ROUTES =====")

for row in rows[:20]:
    print()
    print("Target:", row["settlement_target_key"])
    print("Method:", row["payment_method"])
    print("Currency:", row["currency"])
    print("Expected amount:", row["expected_amount"])
    print("Route status:", row["route_status"])
    print(
        "Payment instructions:",
        row["payment_instructions_status"],
    )
    print("Evidence:", row["evidence"])

conn.close()
