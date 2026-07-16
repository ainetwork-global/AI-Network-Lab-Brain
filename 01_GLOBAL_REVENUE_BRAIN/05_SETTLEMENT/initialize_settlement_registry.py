from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_SETTLEMENT_REGISTRY.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS settlement_targets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        target_key TEXT NOT NULL UNIQUE,
        display_name TEXT NOT NULL,
        provider TEXT NOT NULL,
        rail TEXT NOT NULL,
        supported_currencies TEXT NOT NULL,
        destination_type TEXT NOT NULL,
        configuration_status TEXT NOT NULL,
        verification_status TEXT NOT NULL,
        automatic_receipt_detection INTEGER NOT NULL DEFAULT 0,
        automatic_reconciliation INTEGER NOT NULL DEFAULT 0,
        sensitive_data_stored INTEGER NOT NULL DEFAULT 0,
        notes TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_settlement_targets_status
    ON settlement_targets(
        configuration_status,
        verification_status
    );

    CREATE TABLE IF NOT EXISTS opportunity_settlement_routes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        opportunity_key TEXT NOT NULL,
        settlement_target_key TEXT NOT NULL,
        payment_method TEXT,
        currency TEXT,
        expected_amount REAL,
        minimum_amount REAL,
        payment_instructions_status TEXT NOT NULL DEFAULT 'not_verified',
        route_status TEXT NOT NULL DEFAULT 'candidate',
        human_approval_required INTEGER NOT NULL DEFAULT 1,
        evidence TEXT,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE(opportunity_key, settlement_target_key),
        FOREIGN KEY(settlement_target_key)
            REFERENCES settlement_targets(target_key)
    );

    CREATE INDEX IF NOT EXISTS idx_opportunity_settlement_routes
    ON opportunity_settlement_routes(
        route_status,
        settlement_target_key
    );
    """
)

now = utc_now()

targets = [
    {
        "target_key": "stripe_commercial",
        "display_name": "Stripe Commercial Revenue",
        "provider": "Stripe",
        "rail": "card_and_stripe_payments",
        "supported_currencies": "USD,BRL",
        "destination_type": "payment_processor",
        "configuration_status": "existing_configuration_to_verify",
        "verification_status": "pending_live_receipt_test",
        "automatic_receipt_detection": 1,
        "automatic_reconciliation": 1,
        "notes": (
            "Preferencial para SaaS, assinaturas, créditos, "
            "serviços e pagamentos comerciais."
        ),
    },
    {
        "target_key": "base_usdc_wallet",
        "display_name": "Base USDC Treasury Wallet",
        "provider": "Base",
        "rail": "onchain_usdc",
        "supported_currencies": "USDC",
        "destination_type": "crypto_wallet",
        "configuration_status": "existing_configuration_to_verify",
        "verification_status": "pending_live_receipt_test",
        "automatic_receipt_detection": 1,
        "automatic_reconciliation": 1,
        "notes": (
            "Preferencial para recompensas on-chain, agentes, "
            "micropagamentos e oportunidades que paguem em USDC."
        ),
    },
    {
        "target_key": "nomad_usd",
        "display_name": "Nomad USD Account",
        "provider": "Nomad",
        "rail": "bank_transfer",
        "supported_currencies": "USD",
        "destination_type": "bank_account",
        "configuration_status": "account_details_to_verify",
        "verification_status": "pending_receipt_test",
        "automatic_receipt_detection": 0,
        "automatic_reconciliation": 0,
        "notes": (
            "Preferencial quando o pagador oferecer transferência "
            "bancária em USD compatível com os dados da conta."
        ),
    },
]

for target in targets:
    conn.execute(
        """
        INSERT INTO settlement_targets (
            target_key,
            display_name,
            provider,
            rail,
            supported_currencies,
            destination_type,
            configuration_status,
            verification_status,
            automatic_receipt_detection,
            automatic_reconciliation,
            sensitive_data_stored,
            notes,
            created_at,
            updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?)
        ON CONFLICT(target_key) DO UPDATE SET
            display_name = excluded.display_name,
            provider = excluded.provider,
            rail = excluded.rail,
            supported_currencies = excluded.supported_currencies,
            destination_type = excluded.destination_type,
            configuration_status = excluded.configuration_status,
            verification_status = excluded.verification_status,
            automatic_receipt_detection =
                excluded.automatic_receipt_detection,
            automatic_reconciliation =
                excluded.automatic_reconciliation,
            sensitive_data_stored = 0,
            notes = excluded.notes,
            updated_at = excluded.updated_at
        """,
        (
            target["target_key"],
            target["display_name"],
            target["provider"],
            target["rail"],
            target["supported_currencies"],
            target["destination_type"],
            target["configuration_status"],
            target["verification_status"],
            target["automatic_receipt_detection"],
            target["automatic_reconciliation"],
            target["notes"],
            now,
            now,
        ),
    )

conn.commit()

rows = conn.execute(
    """
    SELECT *
    FROM settlement_targets
    ORDER BY id
    """
).fetchall()

lines = [
    "# Global Revenue Brain — Settlement Registry",
    "",
    f"Gerado em: {now}",
    "",
    "Nenhum segredo, chave, endereço bancário ou credencial foi gravado.",
    "",
    "## Destinos",
    "",
]

print()
print("===== SETTLEMENT TARGETS =====")

for row in rows:
    print()
    print(f"Target: {row['target_key']}")
    print(f"Provider: {row['provider']}")
    print(f"Rail: {row['rail']}")
    print(f"Currencies: {row['supported_currencies']}")
    print(f"Configuration: {row['configuration_status']}")
    print(f"Verification: {row['verification_status']}")
    print(
        "Automatic detection:",
        bool(row["automatic_receipt_detection"]),
    )

    lines.extend([
        f"### {row['display_name']}",
        "",
        f"- Chave: `{row['target_key']}`",
        f"- Provedor: {row['provider']}",
        f"- Rail: {row['rail']}",
        f"- Moedas: {row['supported_currencies']}",
        f"- Configuração: **{row['configuration_status']}**",
        f"- Verificação: **{row['verification_status']}**",
        f"- Detecção automática: "
        f"{'sim' if row['automatic_receipt_detection'] else 'não'}",
        f"- Reconciliação automática: "
        f"{'sim' if row['automatic_reconciliation'] else 'não'}",
        f"- Observação: {row['notes']}",
        "",
    ])

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("Targets registered:", len(rows))
print("Sensitive data stored: 0")

conn.close()
