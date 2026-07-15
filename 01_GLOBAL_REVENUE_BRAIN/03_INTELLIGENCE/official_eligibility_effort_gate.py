from __future__ import annotations

import csv
import html
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_OFFICIAL_ELIGIBILITY_GATE.md"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "official_eligible_queue.csv"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; GlobalRevenueBrain/1.2; "
        "+https://github.com/ainetwork-global/AI-Network-Lab-Brain)"
    ),
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
}

GRANT_US_ONLY_TERMS = (
    "state governments",
    "county governments",
    "city or township governments",
    "public and state controlled institutions",
    "private institutions of higher education",
    "native american tribal governments",
    "independent school districts",
    "public housing authorities",
    "nonprofits having a 501(c)(3)",
    "small businesses",
    "unrestricted organizations other than individuals",
    "domestic organizations",
    "united states organizations",
    "u.s. organizations",
)

GRANT_INTERNATIONAL_TERMS = (
    "foreign organizations",
    "non-domestic entities",
    "international organizations",
    "foreign institutions",
    "worldwide eligibility",
    "non-u.s. organizations",
)

INDIVIDUAL_TERMS = (
    "individuals",
    "individual applicants",
    "natural persons",
)

REGISTRATION_TERMS = (
    "sam.gov",
    "unique entity identifier",
    "uei",
    "grants.gov registration",
)

IMMUNEFI_KYC_TERMS = (
    "kyc required",
    "know your customer",
    "identity verification",
    "proof of identity",
)

IMMUNEFI_POC_TERMS = (
    "proof of concept required",
    "poc required",
    "working proof of concept",
)

IMMUNEFI_HIGH_SKILL_TERMS = (
    "smart contract",
    "blockchain",
    "protocol",
    "cryptography",
    "web3",
    "solidity",
    "consensus",
    "bridge",
    "oracle",
)

SECURITY_SCOPE_TERMS = (
    "in scope",
    "out of scope",
    "assets in scope",
    "program rules",
    "responsible disclosure",
)

MONEY_PATTERNS = [
    re.compile(
        r"(?:award ceiling|estimated total program funding|maximum award|maximum bounty)"
        r"[^$\d]{0,100}"
        r"(?:US\$|USD|\$)\s*(\d[\d,.]*(?:\s*[kKmM])?)",
        re.I,
    ),
    re.compile(
        r"(?:US\$|USD|\$)\s*(\d[\d,.]*(?:\s*[kKmM])?)"
        r"[^.\n]{0,100}"
        r"(?:award ceiling|maximum bounty|maximum award)",
        re.I,
    ),
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def clean(value: str | None) -> str:
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def parse_amount(raw: str | None) -> float | None:
    if not raw:
        return None

    value = clean(raw).replace(" ", "")
    multiplier = 1.0

    if value.lower().endswith("k"):
        multiplier = 1_000.0
        value = value[:-1]
    elif value.lower().endswith("m"):
        multiplier = 1_000_000.0
        value = value[:-1]

    value = re.sub(r"[^\d,.-]", "", value)

    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        parts = value.split(",")

        if len(parts[-1]) in {1, 2}:
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")

    try:
        return float(value) * multiplier
    except ValueError:
        return None


def fetch_text(url: str) -> tuple[int | None, str, str | None]:
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=30,
            allow_redirects=True,
        )

        if response.status_code >= 400:
            return response.status_code, "", f"HTTP {response.status_code}"

        soup = BeautifulSoup(response.text, "html.parser")

        for element in soup(["script", "style", "noscript", "svg"]):
            element.decompose()

        text = clean(soup.get_text(" ", strip=True))
        return response.status_code, text[:1_500_000], None

    except requests.RequestException as error:
        return None, "", str(error)


def ensure_columns(connection: sqlite3.Connection) -> None:
    columns = {
        row[1]
        for row in connection.execute(
            "PRAGMA table_info(official_source_candidates)"
        ).fetchall()
    }

    additions = {
        "eligibility_status": "TEXT",
        "eligibility_reason": "TEXT",
        "international_eligibility": "TEXT",
        "individual_eligibility": "TEXT",
        "registration_required": "INTEGER",
        "technical_difficulty": "TEXT",
        "estimated_hours": "REAL",
        "time_to_revenue_days": "INTEGER",
        "success_probability": "REAL",
        "expected_value_usd": "REAL",
        "effort_adjusted_score": "REAL",
        "human_approval_required": "INTEGER",
        "detail_http_status": "INTEGER",
        "eligibility_checked_at": "TEXT",
    }

    for column, data_type in additions.items():
        if column not in columns:
            connection.execute(
                f"ALTER TABLE official_source_candidates "
                f"ADD COLUMN {column} {data_type}"
            )

    connection.commit()


def extract_money(text: str) -> float | None:
    for pattern in MONEY_PATTERNS:
        match = pattern.search(text)

        if match:
            amount = parse_amount(match.group(1))

            if amount:
                return amount

    return None


def classify_grant(row: sqlite3.Row, text: str) -> dict:
    lowered = text.lower()
    reasons: list[str] = []

    international = any(
        term in lowered
        for term in GRANT_INTERNATIONAL_TERMS
    )

    us_entity_language = any(
        term in lowered
        for term in GRANT_US_ONLY_TERMS
    )

    individuals_allowed = any(
        term in lowered
        for term in INDIVIDUAL_TERMS
    )

    registration_required = any(
        term in lowered
        for term in REGISTRATION_TERMS
    )

    reward_amount = row["reward_amount"] or extract_money(text)

    if international:
        international_status = "explicitly_allowed"
        reasons.append("O texto oficial menciona entidades estrangeiras ou internacionais.")
    elif us_entity_language:
        international_status = "likely_restricted"
        reasons.append("O texto oficial prioriza categorias de entidades dos Estados Unidos.")
    else:
        international_status = "unknown"
        reasons.append("Elegibilidade internacional não pôde ser confirmada.")

    individual_status = (
        "allowed"
        if individuals_allowed
        else "not_confirmed"
    )

    if individuals_allowed:
        reasons.append("Candidatura individual aparece entre as categorias elegíveis.")
    else:
        reasons.append("Candidatura individual não foi confirmada.")

    if registration_required:
        reasons.append("Cadastro institucional, Grants.gov, SAM.gov ou UEI pode ser obrigatório.")

    title = (row["title"] or "").lower()

    institutional_terms = (
        "university",
        "research",
        "science",
        "institute",
        "agency",
        "military",
        "navy",
        "marine corps",
        "nih",
        "nsf",
        "transportation",
    )

    institutional_complexity = any(
        term in title
        for term in institutional_terms
    )

    if international and individuals_allowed:
        eligibility_status = "potentially_eligible"
        probability = 0.08
        estimated_hours = 80.0
    elif international:
        eligibility_status = "entity_required"
        probability = 0.04
        estimated_hours = 120.0
    elif us_entity_language:
        eligibility_status = "likely_ineligible"
        probability = 0.005
        estimated_hours = 120.0
    else:
        eligibility_status = "manual_eligibility_review"
        probability = 0.015
        estimated_hours = 100.0

    if institutional_complexity:
        probability *= 0.7
        estimated_hours += 40
        reasons.append("A oportunidade aparenta exigir capacidade institucional ou científica.")

    time_to_revenue_days = 240
    technical_difficulty = "very_high"

    expected_value = (
        float(reward_amount) * probability
        if reward_amount
        else 0.0
    )

    effort_score = (
        expected_value / max(estimated_hours, 1)
    )

    if eligibility_status == "likely_ineligible":
        effort_score = 0.0

    return {
        "eligibility_status": eligibility_status,
        "eligibility_reason": "; ".join(dict.fromkeys(reasons)),
        "international_eligibility": international_status,
        "individual_eligibility": individual_status,
        "registration_required": int(registration_required),
        "technical_difficulty": technical_difficulty,
        "estimated_hours": estimated_hours,
        "time_to_revenue_days": time_to_revenue_days,
        "success_probability": round(probability, 4),
        "expected_value_usd": round(expected_value, 2),
        "effort_adjusted_score": round(min(100, effort_score), 4),
        "human_approval_required": 1,
        "reward_amount": reward_amount,
    }


def classify_immunefi(row: sqlite3.Row, text: str) -> dict:
    lowered = text.lower()
    reasons: list[str] = []

    kyc_required = any(
        term in lowered
        for term in IMMUNEFI_KYC_TERMS
    )

    poc_required = any(
        term in lowered
        for term in IMMUNEFI_POC_TERMS
    )

    high_skill = any(
        term in lowered
        for term in IMMUNEFI_HIGH_SKILL_TERMS
    )

    scope_confirmed = any(
        term in lowered
        for term in SECURITY_SCOPE_TERMS
    )

    reward_amount = row["reward_amount"] or extract_money(text) or 0.0

    if kyc_required:
        reasons.append("KYC ou verificação de identidade foi identificado.")

    if poc_required:
        reasons.append("Prova de conceito técnica pode ser obrigatória.")

    if scope_confirmed:
        reasons.append("O programa possui escopo e regras oficiais.")
    else:
        reasons.append("O escopo precisa ser revisado manualmente antes de qualquer teste.")

    reasons.append(
        "Somente testes explicitamente autorizados e dentro do escopo são permitidos."
    )

    if high_skill:
        technical_difficulty = "very_high"
        estimated_hours = 120.0
        probability = 0.002
    else:
        technical_difficulty = "high"
        estimated_hours = 80.0
        probability = 0.003

    if poc_required:
        estimated_hours += 30
        probability *= 0.8

    expected_value = reward_amount * probability
    effort_score = expected_value / max(estimated_hours, 1)

    return {
        "eligibility_status": "specialist_only",
        "eligibility_reason": "; ".join(dict.fromkeys(reasons)),
        "international_eligibility": "program_specific",
        "individual_eligibility": "likely_allowed_subject_to_rules",
        "registration_required": int(kyc_required),
        "technical_difficulty": technical_difficulty,
        "estimated_hours": estimated_hours,
        "time_to_revenue_days": 45,
        "success_probability": round(probability, 4),
        "expected_value_usd": round(expected_value, 2),
        "effort_adjusted_score": round(min(100, effort_score), 4),
        "human_approval_required": 1,
        "reward_amount": reward_amount,
    }


connection = sqlite3.connect(DATABASE)
connection.row_factory = sqlite3.Row

ensure_columns(connection)

rows = connection.execute(
    """
    SELECT *
    FROM official_source_candidates
    WHERE verification_status = 'staged'
    ORDER BY
        CASE source_name
            WHEN 'Immunefi' THEN 1
            WHEN 'Grants.gov API' THEN 2
            ELSE 3
        END,
        candidate_score DESC,
        reward_amount DESC
    LIMIT 60
    """
).fetchall()

results = []
errors = 0

print()
print("===== OFFICIAL ELIGIBILITY & EFFORT GATE =====")
print(f"Selecionadas: {len(rows)}")

for index, row in enumerate(rows, start=1):
    print()
    print(f"[{index}/{len(rows)}] {row['title']}")
    print(f"Fonte: {row['source_name']}")

    http_status, text, error = fetch_text(row["url"])

    if error:
        errors += 1
        result = {
            "eligibility_status": "verification_error",
            "eligibility_reason": error,
            "international_eligibility": "unknown",
            "individual_eligibility": "unknown",
            "registration_required": 0,
            "technical_difficulty": "unknown",
            "estimated_hours": 0.0,
            "time_to_revenue_days": 0,
            "success_probability": 0.0,
            "expected_value_usd": 0.0,
            "effort_adjusted_score": 0.0,
            "human_approval_required": 1,
            "reward_amount": row["reward_amount"],
        }

    elif row["source_name"] == "Grants.gov API":
        result = classify_grant(row, text)

    elif row["source_name"] == "Immunefi":
        result = classify_immunefi(row, text)

    else:
        result = {
            "eligibility_status": "manual_review",
            "eligibility_reason": "Fonte sem adaptador de elegibilidade.",
            "international_eligibility": "unknown",
            "individual_eligibility": "unknown",
            "registration_required": 0,
            "technical_difficulty": "unknown",
            "estimated_hours": 0.0,
            "time_to_revenue_days": 0,
            "success_probability": 0.0,
            "expected_value_usd": 0.0,
            "effort_adjusted_score": 0.0,
            "human_approval_required": 1,
            "reward_amount": row["reward_amount"],
        }

    connection.execute(
        """
        UPDATE official_source_candidates
        SET
            reward_amount = COALESCE(?, reward_amount),
            eligibility_status = ?,
            eligibility_reason = ?,
            international_eligibility = ?,
            individual_eligibility = ?,
            registration_required = ?,
            technical_difficulty = ?,
            estimated_hours = ?,
            time_to_revenue_days = ?,
            success_probability = ?,
            expected_value_usd = ?,
            effort_adjusted_score = ?,
            human_approval_required = ?,
            detail_http_status = ?,
            eligibility_checked_at = ?
        WHERE id = ?
        """,
        (
            result["reward_amount"],
            result["eligibility_status"],
            result["eligibility_reason"],
            result["international_eligibility"],
            result["individual_eligibility"],
            result["registration_required"],
            result["technical_difficulty"],
            result["estimated_hours"],
            result["time_to_revenue_days"],
            result["success_probability"],
            result["expected_value_usd"],
            result["effort_adjusted_score"],
            result["human_approval_required"],
            http_status,
            utc_now(),
            row["id"],
        ),
    )

    connection.commit()

    item = {
        "id": row["id"],
        "title": row["title"],
        "source_name": row["source_name"],
        "category": row["category"],
        "url": row["url"],
        "reward_amount": result["reward_amount"],
        "reward_currency": row["reward_currency"],
        **result,
    }

    results.append(item)

    print(f"Elegibilidade: {result['eligibility_status']}")
    print(f"Probabilidade: {result['success_probability'] * 100:.2f}%")
    print(f"Valor esperado: USD {result['expected_value_usd']:.2f}")
    print(f"Score por esforço: {result['effort_adjusted_score']:.4f}")

    time.sleep(0.25)

results.sort(
    key=lambda item: (
        item["eligibility_status"] in {
            "likely_ineligible",
            "verification_error",
        },
        -item["effort_adjusted_score"],
        -item["expected_value_usd"],
    )
)

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "id",
    "title",
    "source_name",
    "category",
    "url",
    "reward_amount",
    "reward_currency",
    "eligibility_status",
    "eligibility_reason",
    "international_eligibility",
    "individual_eligibility",
    "registration_required",
    "technical_difficulty",
    "estimated_hours",
    "time_to_revenue_days",
    "success_probability",
    "expected_value_usd",
    "effort_adjusted_score",
    "human_approval_required",
]

with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

counts: dict[str, int] = {}

for item in results:
    status = item["eligibility_status"]
    counts[status] = counts.get(status, 0) + 1

lines = [
    "# Global Revenue Brain — Official Eligibility & Effort Gate",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Resumo",
    "",
    f"- Total analisado: **{len(results)}**",
    f"- Potentially eligible: **{counts.get('potentially_eligible', 0)}**",
    f"- Entity required: **{counts.get('entity_required', 0)}**",
    f"- Manual eligibility review: **{counts.get('manual_eligibility_review', 0)}**",
    f"- Specialist only: **{counts.get('specialist_only', 0)}**",
    f"- Likely ineligible: **{counts.get('likely_ineligible', 0)}**",
    f"- Erros: **{errors}**",
    "",
    "## Ranking ajustado por esforço",
    "",
]

for index, item in enumerate(results, start=1):
    reward = (
        f"{item['reward_currency'] or 'USD'} "
        f"{float(item['reward_amount']):,.2f}"
        if item["reward_amount"]
        else "não identificada"
    )

    lines.extend(
        [
            f"### {index}. {item['title']}",
            "",
            f"- Fonte: {item['source_name']}",
            f"- Elegibilidade: **{item['eligibility_status']}**",
            f"- Recompensa máxima: {reward}",
            f"- Probabilidade estimada: {item['success_probability'] * 100:.3f}%",
            f"- Valor esperado: USD {item['expected_value_usd']:,.2f}",
            f"- Horas estimadas: {item['estimated_hours']}",
            f"- Tempo até receita: {item['time_to_revenue_days']} dias",
            f"- Score por esforço: **{item['effort_adjusted_score']}**",
            f"- Dificuldade: {item['technical_difficulty']}",
            f"- Elegibilidade internacional: {item['international_eligibility']}",
            f"- Elegibilidade individual: {item['individual_eligibility']}",
            f"- Cadastro obrigatório: {'sim' if item['registration_required'] else 'não identificado'}",
            f"- Aprovação humana: sim",
            f"- Motivo: {item['eligibility_reason']}",
            f"- URL: {item['url']}",
            "",
        ]
    )

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== ELIGIBILITY SUMMARY =====")
print(f"Analisadas: {len(results)}")
print(f"Potentially eligible: {counts.get('potentially_eligible', 0)}")
print(f"Entity required: {counts.get('entity_required', 0)}")
print(f"Manual eligibility review: {counts.get('manual_eligibility_review', 0)}")
print(f"Specialist only: {counts.get('specialist_only', 0)}")
print(f"Likely ineligible: {counts.get('likely_ineligible', 0)}")
print(f"Erros: {errors}")

print()
print("===== TOP 15 BY EXPECTED VALUE PER EFFORT =====")

for index, item in enumerate(results[:15], start=1):
    reward = (
        f"{item['reward_currency'] or 'USD'} {item['reward_amount']}"
        if item["reward_amount"]
        else "não identificada"
    )

    print()
    print(f"{index}. {item['title']}")
    print(f"   fonte: {item['source_name']}")
    print(f"   elegibilidade: {item['eligibility_status']}")
    print(f"   recompensa máxima: {reward}")
    print(f"   probabilidade: {item['success_probability'] * 100:.3f}%")
    print(f"   valor esperado: USD {item['expected_value_usd']}")
    print(f"   horas estimadas: {item['estimated_hours']}")
    print(f"   score por esforço: {item['effort_adjusted_score']}")
    print(f"   url: {item['url']}")

connection.close()
