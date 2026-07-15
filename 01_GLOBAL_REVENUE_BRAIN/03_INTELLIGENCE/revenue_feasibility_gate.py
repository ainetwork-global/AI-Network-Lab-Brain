from __future__ import annotations

import csv
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "feasible_revenue_queue.csv"
REPORT_PATH = ROOT / "12_REPORTS" / "LATEST_REVENUE_FEASIBILITY_GATE.md"


IMPOSSIBLE_PATTERNS = {
    r"\bexact value of pi\b": (
        "A representação decimal exata completa de π é infinita e não pode ser "
        "entregue como valor decimal final."
    ),
    r"\bcalculate pi exactly\b": "Tarefa matematicamente impossível no sentido literal.",
    r"\bperpetual motion\b": "Proposta incompatível com princípios físicos conhecidos.",
    r"\bsolve p\s*=\s*np\b": "Problema matemático aberto sem solução conhecida.",
    r"\bprove the riemann hypothesis\b": "Problema matemático aberto sem solução conhecida.",
    r"\bguaranteed profit\b": "Promessa financeira incompatível com política de risco.",
    r"\bguaranteed return\b": "Promessa financeira incompatível com política de risco.",
}

AGGREGATOR_PATTERNS = (
    "awesome-agent-bounties",
    "bounty alert",
    "new opportunities",
    "opportunity roundup",
    "curated list",
    "weekly bounty",
)

TEST_PATTERNS = (
    "canary",
    "test bounty",
    "demo bounty",
    "example bounty",
    "proof-of-concept payout",
)

UNFUNDED_PATTERNS = (
    "unfunded",
    "not funded",
    "0/",
    "funding pending",
    "reward pool empty",
)

APPLICATION_PATTERNS = (
    "grant application",
    "funding proposal",
    "proposal submitted",
)

DIRECT_EXECUTION_TERMS = (
    "submit a pull request",
    "open a pull request",
    "comment to claim",
    "claim this issue",
    "apply by commenting",
    "submission instructions",
    "deliverables",
    "acceptance criteria",
    "how to apply",
    "how to submit",
)

AUTHORIZED_SECURITY_TERMS = (
    "bug bounty",
    "responsible disclosure",
    "security policy",
    "scope",
    "authorized testing",
)

DANGEROUS_SECURITY_TERMS = (
    "exploit any target",
    "attack production",
    "steal",
    "bypass authentication",
    "access private data",
    "without permission",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def ensure_columns(conn: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in conn.execute(
            "PRAGMA table_info(opportunity_verifications)"
        ).fetchall()
    }

    additions = {
        "feasibility_status": "TEXT",
        "feasibility_score": "REAL",
        "feasibility_reason": "TEXT",
        "execution_mechanism_confirmed": "INTEGER",
        "impossibility_detected": "INTEGER",
        "aggregator_detected": "INTEGER",
        "duplicate_group": "TEXT",
        "feasibility_checked_at": "TEXT",
    }

    for name, data_type in additions.items():
        if name not in columns:
            conn.execute(
                f"ALTER TABLE opportunity_verifications "
                f"ADD COLUMN {name} {data_type}"
            )

    conn.commit()


def find_impossibility(text: str) -> str | None:
    for pattern, reason in IMPOSSIBLE_PATTERNS.items():
        if re.search(pattern, text, re.IGNORECASE):
            return reason
    return None


def contains_any(text: str, terms: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def normalize_title(title: str) -> str:
    value = title.lower()
    value = re.sub(r"\[[^\]]+\]", " ", value)
    value = re.sub(r"[^a-z0-9]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def classify(row: sqlite3.Row, duplicate_count: int):
    title = row["title"] or ""
    reason_text = row["deep_verification_reason"] or ""
    labels = row["github_labels"] or ""
    url = row["url"] or ""

    combined = f"{title}\n{reason_text}\n{labels}\n{url}"
    lowered = combined.lower()

    reasons: list[str] = []
    score = float(row["deep_verification_score"] or 0)

    impossibility_reason = find_impossibility(combined)
    aggregator = contains_any(combined, AGGREGATOR_PATTERNS)
    test_record = contains_any(combined, TEST_PATTERNS)
    unfunded = contains_any(combined, UNFUNDED_PATTERNS)
    submitted_application = contains_any(combined, APPLICATION_PATTERNS)

    execution_mechanism = contains_any(
        combined,
        DIRECT_EXECUTION_TERMS,
    )

    issue_open = row["github_issue_state"] == "open"
    repository_active = not bool(row["github_repo_archived"]) and not bool(
        row["github_repo_disabled"]
    )

    if impossibility_reason:
        score = 0
        reasons.append(impossibility_reason)

    if aggregator:
        score -= 70
        reasons.append(
            "Registro pertence a agregador ou catálogo; é necessário localizar "
            "a oportunidade original."
        )

    if duplicate_count > 1:
        score -= 15
        reasons.append(
            f"O mesmo título normalizado aparece {duplicate_count} vezes."
        )

    if test_record:
        score -= 50
        reasons.append("Registro aparenta ser teste, demonstração ou canário.")

    if unfunded:
        score -= 80
        reasons.append("Recompensa não financiada ou financiamento pendente.")

    if submitted_application:
        score -= 60
        reasons.append(
            "Registro aparenta ser candidatura já submetida, não chamada aberta."
        )

    if not issue_open:
        score -= 70
        reasons.append("Issue não está aberta.")

    if not repository_active:
        score -= 70
        reasons.append("Repositório arquivado ou desativado.")

    if execution_mechanism:
        score += 15
        reasons.append("Mecanismo explícito de execução identificado.")
    else:
        score -= 20
        reasons.append("Mecanismo claro de candidatura ou entrega não identificado.")

    if row["reward_amount"] is None:
        score -= 20
        reasons.append("Recompensa monetária não confirmada.")

    title_lower = title.lower()

    security_related = any(
        term in title_lower
        for term in ("bug", "exploit", "security", "vulnerability")
    )

    if security_related:
        authorized = contains_any(combined, AUTHORIZED_SECURITY_TERMS)
        dangerous = contains_any(combined, DANGEROUS_SECURITY_TERMS)

        if dangerous:
            score = 0
            reasons.append("Atividade de segurança potencialmente não autorizada.")
        elif not authorized:
            score -= 35
            reasons.append(
                "Escopo e autorização de teste de segurança não foram confirmados."
            )
        else:
            reasons.append("Indícios de programa autorizado de segurança encontrados.")

    score = round(max(0, min(100, score)), 2)

    if impossibility_reason or unfunded or test_record:
        status = "feasibility_rejected"
    elif aggregator:
        status = "source_resolution_required"
    elif score >= 75 and execution_mechanism:
        status = "feasible_actionable"
    elif score >= 50:
        status = "human_review_required"
    else:
        status = "feasibility_rejected"

    if not reasons:
        reasons.append("Nenhum impedimento crítico detectado.")

    return {
        "status": status,
        "score": score,
        "reason": "; ".join(dict.fromkeys(reasons)),
        "execution_mechanism": int(execution_mechanism),
        "impossibility": int(bool(impossibility_reason)),
        "aggregator": int(aggregator),
    }


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
ensure_columns(conn)

rows = conn.execute(
    """
    SELECT *
    FROM opportunity_verifications
    WHERE origin = 'external'
      AND deep_verification_status IN (
          'deep_actionable',
          'manual_review'
      )
    ORDER BY deep_verification_score DESC
    """
).fetchall()

normalized_counts: dict[str, int] = {}

for row in rows:
    key = normalize_title(row["title"] or "")
    normalized_counts[key] = normalized_counts.get(key, 0) + 1

results = []

print()
print("===== REVENUE FEASIBILITY GATE =====")
print(f"Selecionadas: {len(rows)}")

for index, row in enumerate(rows, 1):
    duplicate_key = normalize_title(row["title"] or "")
    duplicate_count = normalized_counts.get(duplicate_key, 1)

    result = classify(row, duplicate_count)

    conn.execute(
        """
        UPDATE opportunity_verifications
        SET
            feasibility_status = ?,
            feasibility_score = ?,
            feasibility_reason = ?,
            execution_mechanism_confirmed = ?,
            impossibility_detected = ?,
            aggregator_detected = ?,
            duplicate_group = ?,
            feasibility_checked_at = ?
        WHERE id = ?
        """,
        (
            result["status"],
            result["score"],
            result["reason"],
            result["execution_mechanism"],
            result["impossibility"],
            result["aggregator"],
            duplicate_key if duplicate_count > 1 else None,
            utc_now(),
            row["id"],
        ),
    )

    item = {
        "id": row["id"],
        "title": row["title"],
        "url": row["url"],
        "reward_amount": row["reward_amount"],
        "reward_currency": row["reward_currency"],
        "deep_status": row["deep_verification_status"],
        "deep_score": row["deep_verification_score"],
        "feasibility_status": result["status"],
        "feasibility_score": result["score"],
        "execution_mechanism_confirmed": result["execution_mechanism"],
        "impossibility_detected": result["impossibility"],
        "aggregator_detected": result["aggregator"],
        "duplicate_count": duplicate_count,
        "reason": result["reason"],
    }

    results.append(item)

    print()
    print(f"[{index}/{len(rows)}] {row['title']}")
    print(f"status: {result['status']}")
    print(f"score: {result['score']}")
    print(f"motivo: {result['reason']}")

conn.commit()

status_order = {
    "feasible_actionable": 1,
    "human_review_required": 2,
    "source_resolution_required": 3,
    "feasibility_rejected": 4,
}

results.sort(
    key=lambda item: (
        status_order.get(item["feasibility_status"], 9),
        -item["feasibility_score"],
    )
)

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "id",
    "title",
    "url",
    "reward_amount",
    "reward_currency",
    "deep_status",
    "deep_score",
    "feasibility_status",
    "feasibility_score",
    "execution_mechanism_confirmed",
    "impossibility_detected",
    "aggregator_detected",
    "duplicate_count",
    "reason",
]

with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

counts: dict[str, int] = {}

for result in results:
    status = result["feasibility_status"]
    counts[status] = counts.get(status, 0) + 1

lines = [
    "# Global Revenue Brain — Revenue Feasibility Gate",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Resumo",
    "",
    f"- Total analisado: **{len(results)}**",
    f"- Feasible actionable: **{counts.get('feasible_actionable', 0)}**",
    f"- Human review required: **{counts.get('human_review_required', 0)}**",
    f"- Source resolution required: **{counts.get('source_resolution_required', 0)}**",
    f"- Rejected: **{counts.get('feasibility_rejected', 0)}**",
    "",
    "## Resultados",
    "",
]

for index, result in enumerate(results, 1):
    reward = "não confirmada"

    if result["reward_amount"] is not None:
        reward = (
            f"{result['reward_currency'] or '?'} "
            f"{result['reward_amount']}"
        )

    lines.extend([
        f"### {index}. {result['title']}",
        "",
        f"- Status: **{result['feasibility_status']}**",
        f"- Score de viabilidade: **{result['feasibility_score']}**",
        f"- Recompensa anterior: {reward}",
        f"- Mecanismo de execução confirmado: "
        f"{'sim' if result['execution_mechanism_confirmed'] else 'não'}",
        f"- Impossibilidade detectada: "
        f"{'sim' if result['impossibility_detected'] else 'não'}",
        f"- Agregador detectado: "
        f"{'sim' if result['aggregator_detected'] else 'não'}",
        f"- Duplicatas: {result['duplicate_count']}",
        f"- Motivo: {result['reason']}",
        f"- URL: {result['url']}",
        "",
    ])

REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== FEASIBILITY SUMMARY =====")
print(f"Analisadas: {len(results)}")
print(f"Feasible actionable: {counts.get('feasible_actionable', 0)}")
print(f"Human review required: {counts.get('human_review_required', 0)}")
print(f"Source resolution required: {counts.get('source_resolution_required', 0)}")
print(f"Rejected: {counts.get('feasibility_rejected', 0)}")

print()
print("===== FEASIBLE ACTIONABLE =====")

for index, result in enumerate(
    [
        item for item in results
        if item["feasibility_status"] == "feasible_actionable"
    ],
    1,
):
    print()
    print(f"{index}. {result['title']}")
    print(f"   score: {result['feasibility_score']}")
    print(
        f"   recompensa: {result['reward_currency']} "
        f"{result['reward_amount']}"
    )
    print(f"   motivo: {result['reason']}")
    print(f"   url: {result['url']}")

conn.close()
