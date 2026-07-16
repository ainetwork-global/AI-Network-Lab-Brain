from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_SETTLEMENT_ROUTE_VERIFICATION.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS settlement_route_verifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        route_id INTEGER NOT NULL UNIQUE,
        opportunity_key TEXT NOT NULL,
        settlement_target_key TEXT NOT NULL,
        claimed_payment_method TEXT,
        claimed_currency TEXT,
        explicit_payment_evidence INTEGER NOT NULL DEFAULT 0,
        official_instructions_found INTEGER NOT NULL DEFAULT 0,
        destination_compatible INTEGER NOT NULL DEFAULT 0,
        verification_status TEXT NOT NULL,
        verification_reason TEXT NOT NULL,
        verified_at TEXT NOT NULL,
        FOREIGN KEY(route_id)
            REFERENCES opportunity_settlement_routes(id)
    );

    CREATE INDEX IF NOT EXISTS idx_route_verification_status
    ON settlement_route_verifications(
        verification_status,
        settlement_target_key
    );
    """
)

routes = conn.execute(
    """
    SELECT
        r.id,
        r.opportunity_key,
        r.settlement_target_key,
        r.payment_method,
        r.currency,
        r.expected_amount,
        r.route_status,
        r.payment_instructions_status,
        r.evidence,
        t.display_name
    FROM opportunity_settlement_routes r
    JOIN settlement_targets t
      ON t.target_key = r.settlement_target_key
    ORDER BY COALESCE(r.expected_amount, 0) DESC
    """
).fetchall()

results = []
now = utc_now()

print()
print("===== SETTLEMENT ROUTE VERIFICATION =====")
print("Routes analyzed:", len(routes))

for route in routes:
    evidence = (route["evidence"] or "").lower()

    # O roteador anterior usou palavras presentes no título ou contexto.
    # Isso não é evidência explícita de pagamento.
    explicit_payment_evidence = 0
    official_instructions_found = 0
    destination_compatible = 0

    verification_status = "payment_evidence_required"
    reason = (
        "Oportunidade roteada por inferência textual. "
        "Não foram encontradas instruções oficiais que confirmem "
        "método de pagamento, moeda, destino ou processo de resgate."
    )

    conn.execute(
        """
        INSERT INTO settlement_route_verifications (
            route_id,
            opportunity_key,
            settlement_target_key,
            claimed_payment_method,
            claimed_currency,
            explicit_payment_evidence,
            official_instructions_found,
            destination_compatible,
            verification_status,
            verification_reason,
            verified_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(route_id) DO UPDATE SET
            claimed_payment_method =
                excluded.claimed_payment_method,
            claimed_currency =
                excluded.claimed_currency,
            explicit_payment_evidence =
                excluded.explicit_payment_evidence,
            official_instructions_found =
                excluded.official_instructions_found,
            destination_compatible =
                excluded.destination_compatible,
            verification_status =
                excluded.verification_status,
            verification_reason =
                excluded.verification_reason,
            verified_at =
                excluded.verified_at
        """,
        (
            route["id"],
            route["opportunity_key"],
            route["settlement_target_key"],
            route["payment_method"],
            route["currency"],
            explicit_payment_evidence,
            official_instructions_found,
            destination_compatible,
            verification_status,
            reason,
            now,
        ),
    )

    conn.execute(
        """
        UPDATE opportunity_settlement_routes
        SET
            route_status = 'review_required',
            payment_instructions_status =
                'explicit_evidence_required',
            human_approval_required = 1,
            updated_at = ?
        WHERE id = ?
        """,
        (now, route["id"]),
    )

    results.append({
        "target": route["settlement_target_key"],
        "display_name": route["display_name"],
        "method": route["payment_method"],
        "currency": route["currency"],
        "expected_amount": route["expected_amount"],
        "status": verification_status,
        "reason": reason,
        "evidence": route["evidence"],
    })

conn.commit()

lines = [
    "# Settlement Route Verification",
    "",
    f"Gerado em: {now}",
    "",
    "Nenhuma movimentação financeira foi realizada.",
    "",
    "## Resumo",
    "",
    f"- Rotas analisadas: **{len(results)}**",
    f"- Rotas confirmadas: **0**",
    f"- Evidência explícita necessária: **{len(results)}**",
    "",
    "As rotas anteriores foram rebaixadas para revisão porque "
    "palavras no título não comprovam a forma real de pagamento.",
    "",
    "## Resultados",
    "",
]

for index, item in enumerate(results, 1):
    lines.extend([
        f"### {index}. {item['display_name']}",
        "",
        f"- Destino inferido: `{item['target']}`",
        f"- Método inferido: {item['method']}",
        f"- Moeda inferida: {item['currency']}",
        f"- Valor esperado: "
        f"{item['expected_amount'] if item['expected_amount'] is not None else 'não identificado'}",
        f"- Status: **{item['status']}**",
        f"- Motivo: {item['reason']}",
        f"- Evidência anterior: {item['evidence']}",
        "",
    ])

REPORT.write_text("\n".join(lines), encoding="utf-8")

print("Confirmed routes: 0")
print("Payment evidence required:", len(results))

print()
print("===== ROUTE STATUS =====")

for item in results:
    print()
    print("Target:", item["target"])
    print("Expected amount:", item["expected_amount"])
    print("Status:", item["status"])
    print("Reason:", item["reason"])

conn.close()
