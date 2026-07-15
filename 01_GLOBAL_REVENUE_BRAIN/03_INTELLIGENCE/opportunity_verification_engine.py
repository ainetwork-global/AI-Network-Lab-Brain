from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sqlite3
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dateutil import parser as date_parser


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATABASE_PATH = PROJECT_ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT_PATH = PROJECT_ROOT / "12_REPORTS" / "LATEST_VERIFIED_OPPORTUNITIES.md"
CSV_PATH = PROJECT_ROOT / "04_OPPORTUNITIES" / "verified_opportunities.csv"
LOG_PATH = PROJECT_ROOT / "09_LOGS" / "opportunity_verification.log"

ALLOWED_STATUSES = {
    "discovered",
    "verifying",
    "verified",
    "rejected",
    "actionable",
    "approval_required",
    "preparing",
    "submitted",
    "awaiting_response",
    "won",
    "paid",
    "expired",
}

REWARD_PATTERNS = [
    re.compile(
        r"(?P<currency>US\$|USD|\$|EUR|€|GBP|£|BRL|R\$)\s*"
        r"(?P<amount>\d[\d,.]*(?:\.\d{1,2})?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?P<amount>\d[\d,.]*(?:\.\d{1,2})?)\s*"
        r"(?P<currency>USD|USDC|USDT|EUR|GBP|BRL|ETH|BTC|SOL)",
        re.IGNORECASE,
    ),
]

DEADLINE_PATTERNS = [
    re.compile(
        r"(?:deadline|due date|closing date|closes|submission deadline)"
        r"[\s:–-]+([A-Za-z]{3,9}\s+\d{1,2},?\s+\d{4})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:deadline|due date|closing date|closes|submission deadline)"
        r"[\s:–-]+(\d{4}-\d{2}-\d{2})",
        re.IGNORECASE,
    ),
    re.compile(
        r"(?:deadline|due date|closing date|closes|submission deadline)"
        r"[\s:–-]+(\d{1,2}/\d{1,2}/\d{4})",
        re.IGNORECASE,
    ),
]

POSITIVE_TERMS = {
    "bounty": 12,
    "reward": 12,
    "prize": 10,
    "grant": 10,
    "paid": 8,
    "compensation": 8,
    "contract": 7,
    "cash prize": 12,
    "payment": 6,
    "winner": 5,
    "usd": 4,
    "usdc": 4,
    "open": 3,
    "apply": 3,
    "submission": 3,
}

NEGATIVE_TERMS = {
    "news": 8,
    "announcement": 5,
    "recap": 8,
    "opinion": 7,
    "giveaway": 7,
    "casino": 15,
    "deposit required": 25,
    "investment required": 25,
    "pay to join": 30,
    "send funds": 30,
    "guaranteed profit": 30,
    "seed phrase": 40,
    "private key": 40,
    "closed": 12,
    "completed": 10,
    "expired": 15,
}

CAPITAL_TERMS = [
    "deposit required",
    "entry fee",
    "purchase required",
    "investment required",
    "stake required",
    "pay to join",
    "buy tokens",
    "minimum deposit",
]

KYC_TERMS = [
    "kyc",
    "identity verification",
    "government-issued id",
    "government issued id",
    "proof of identity",
]

HUMAN_APPROVAL_TERMS = [
    "wallet",
    "sign transaction",
    "connect wallet",
    "identity verification",
    "kyc",
    "contract",
    "legal agreement",
    "terms and conditions",
    "entry fee",
]

COUNTRY_PATTERNS = [
    re.compile(r"(?:only available to|open to|eligible countries|eligibility)[^.\n]{0,160}", re.I),
    re.compile(r"(?:residents? of|citizens? of)[^.\n]{0,120}", re.I),
]

REQUIREMENT_PATTERNS = [
    re.compile(r"(?:requirements?|eligibility|who can apply)[\s:–-]+([^.\n]{10,300})", re.I),
    re.compile(r"(?:must have|must be|applicants? must)[\s:–-]*([^.\n]{10,300})", re.I),
]


@dataclass
class VerificationResult:
    opportunity_id: Any
    title: str
    category: str
    source: str
    url: str
    http_status: int | None
    link_active: bool
    executable: bool
    explicit_reward: bool
    reward_amount: float | None
    reward_currency: str | None
    deadline: str | None
    requirements: str | None
    capital_required: bool
    capital_details: str | None
    difficulty: str
    estimated_hours: float
    risk_level: str
    success_probability: float
    country_restrictions: str | None
    kyc_required: bool
    human_approval_required: bool
    payment_method: str | None
    verification_status: str
    recommended_action: str
    recommendation_reason: str
    verification_score: float
    verified_at: str
    page_title: str | None
    failure_reason: str | None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def log(message: str) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    line = f"[{utc_now()}] {message}"
    print(line)
    with LOG_PATH.open("a", encoding="utf-8") as file:
        file.write(line + "\n")


def connect_database() -> sqlite3.Connection:
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    return connection


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = ?
        """,
        (table_name,),
    ).fetchone()
    return row is not None


def get_columns(connection: sqlite3.Connection, table_name: str) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(f'PRAGMA table_info("{table_name}")').fetchall()
    }


def choose_column(columns: set[str], candidates: list[str]) -> str | None:
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def initialize_schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        CREATE TABLE IF NOT EXISTS opportunity_verifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            opportunity_id TEXT NOT NULL,
            title TEXT,
            category TEXT,
            source TEXT,
            url TEXT,
            http_status INTEGER,
            link_active INTEGER NOT NULL DEFAULT 0,
            executable INTEGER NOT NULL DEFAULT 0,
            explicit_reward INTEGER NOT NULL DEFAULT 0,
            reward_amount REAL,
            reward_currency TEXT,
            deadline TEXT,
            requirements TEXT,
            capital_required INTEGER NOT NULL DEFAULT 0,
            capital_details TEXT,
            difficulty TEXT,
            estimated_hours REAL,
            risk_level TEXT,
            success_probability REAL,
            country_restrictions TEXT,
            kyc_required INTEGER NOT NULL DEFAULT 0,
            human_approval_required INTEGER NOT NULL DEFAULT 0,
            payment_method TEXT,
            verification_status TEXT NOT NULL,
            recommended_action TEXT,
            recommendation_reason TEXT,
            verification_score REAL,
            verified_at TEXT NOT NULL,
            page_title TEXT,
            failure_reason TEXT,
            raw_verification_json TEXT,
            UNIQUE(opportunity_id)
        );

        CREATE INDEX IF NOT EXISTS idx_opportunity_verifications_status
        ON opportunity_verifications(verification_status);

        CREATE INDEX IF NOT EXISTS idx_opportunity_verifications_score
        ON opportunity_verifications(verification_score DESC);

        CREATE INDEX IF NOT EXISTS idx_opportunity_verifications_actionable
        ON opportunity_verifications(executable, link_active);

        CREATE TABLE IF NOT EXISTS verification_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            started_at TEXT NOT NULL,
            finished_at TEXT,
            selected_count INTEGER NOT NULL DEFAULT 0,
            verified_count INTEGER NOT NULL DEFAULT 0,
            actionable_count INTEGER NOT NULL DEFAULT 0,
            rejected_count INTEGER NOT NULL DEFAULT 0,
            error_count INTEGER NOT NULL DEFAULT 0,
            run_status TEXT NOT NULL DEFAULT 'running'
        );
        """
    )
    connection.commit()


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", html.unescape(str(value))).strip()


def safe_float(value: Any) -> float | None:
    if value is None or value == "":
        return None

    try:
        if isinstance(value, (int, float)):
            return float(value)

        text = str(value).strip()
        text = re.sub(r"[^\d,.-]", "", text)

        if "," in text and "." in text:
            if text.rfind(",") > text.rfind("."):
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")
        elif "," in text:
            parts = text.split(",")
            if len(parts[-1]) == 2:
                text = text.replace(".", "").replace(",", ".")
            else:
                text = text.replace(",", "")

        return float(text)
    except (TypeError, ValueError):
        return None


def parse_reward(text: str) -> tuple[float | None, str | None, bool]:
    matches: list[tuple[float, str]] = []

    currency_map = {
        "$": "USD",
        "US$": "USD",
        "USD": "USD",
        "R$": "BRL",
        "BRL": "BRL",
        "€": "EUR",
        "EUR": "EUR",
        "£": "GBP",
        "GBP": "GBP",
    }

    for pattern in REWARD_PATTERNS:
        for match in pattern.finditer(text):
            amount = safe_float(match.group("amount"))
            currency_raw = match.group("currency").upper()
            currency = currency_map.get(currency_raw, currency_raw)

            if amount is not None and amount > 0:
                matches.append((amount, currency))

    if not matches:
        return None, None, False

    amount, currency = max(matches, key=lambda item: item[0])
    return amount, currency, True


def parse_deadline(text: str) -> str | None:
    for pattern in DEADLINE_PATTERNS:
        match = pattern.search(text)
        if not match:
            continue

        raw_date = normalize_text(match.group(1))

        try:
            parsed = date_parser.parse(raw_date, fuzzy=True)
            return parsed.date().isoformat()
        except (ValueError, TypeError, OverflowError):
            return raw_date[:100]

    return None


def extract_requirements(text: str) -> str | None:
    for pattern in REQUIREMENT_PATTERNS:
        match = pattern.search(text)
        if match:
            return normalize_text(match.group(1))[:500]
    return None


def extract_country_restrictions(text: str) -> str | None:
    for pattern in COUNTRY_PATTERNS:
        match = pattern.search(text)
        if match:
            return normalize_text(match.group(0))[:400]
    return None


def detect_payment_method(text: str) -> str | None:
    lowered = text.lower()

    methods = [
        ("USDC", ["usdc"]),
        ("USDT", ["usdt"]),
        ("Criptomoeda", ["crypto payment", "cryptocurrency", "wallet address"]),
        ("PayPal", ["paypal"]),
        ("Transferência bancária", ["bank transfer", "wire transfer"]),
        ("Stripe", ["stripe"]),
        ("GitHub Sponsors", ["github sponsors"]),
        ("Cartão-presente", ["gift card"]),
    ]

    found = [name for name, terms in methods if any(term in lowered for term in terms)]
    return ", ".join(found) if found else None


def determine_difficulty(text: str, category: str, reward: float | None) -> tuple[str, float]:
    lowered = f"{category} {text}".lower()

    hard_terms = [
        "production-ready",
        "smart contract",
        "security audit",
        "machine learning model",
        "full stack",
        "protocol implementation",
        "cryptography",
        "zero knowledge",
        "zk proof",
        "senior",
        "expert",
    ]

    easy_terms = [
        "documentation",
        "translation",
        "small fix",
        "good first issue",
        "beginner",
        "simple task",
        "content",
    ]

    hard_score = sum(term in lowered for term in hard_terms)
    easy_score = sum(term in lowered for term in easy_terms)

    if hard_score >= 2 or (reward is not None and reward >= 10_000):
        return "alta", 80.0

    if easy_score >= 1 and hard_score == 0:
        return "baixa", 8.0

    return "média", 30.0


def calculate_risk(
    text: str,
    link_active: bool,
    capital_required: bool,
    explicit_reward: bool,
    executable: bool,
) -> str:
    lowered = text.lower()

    severe_terms = [
        "seed phrase",
        "private key",
        "guaranteed profit",
        "send funds",
        "pay to join",
    ]

    if any(term in lowered for term in severe_terms):
        return "crítico"

    if not link_active or capital_required:
        return "alto"

    if not explicit_reward or not executable:
        return "médio"

    return "baixo"


def fetch_page(url: str, timeout: int) -> tuple[int | None, str, str | None, str | None]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; GlobalRevenueBrain/1.0; "
            "+https://github.com/ainetwork-global/AI-Network-Lab-Brain)"
        ),
        "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
    }

    try:
        response = requests.get(
            url,
            headers=headers,
            timeout=timeout,
            allow_redirects=True,
        )

        content_type = response.headers.get("content-type", "").lower()
        raw_text = response.text[:2_000_000]

        if "json" in content_type:
            try:
                parsed = response.json()
                text = json.dumps(parsed, ensure_ascii=False)
                title = None
            except ValueError:
                text = raw_text
                title = None
        else:
            soup = BeautifulSoup(raw_text, "html.parser")

            for element in soup(["script", "style", "noscript", "svg"]):
                element.decompose()

            title = normalize_text(soup.title.string if soup.title else None)
            text = normalize_text(soup.get_text(" ", strip=True))

        return response.status_code, text, title, None

    except requests.RequestException as exc:
        return None, "", None, str(exc)


def calculate_verification_score(
    *,
    link_active: bool,
    executable: bool,
    explicit_reward: bool,
    reward_amount: float | None,
    deadline: str | None,
    requirements: str | None,
    capital_required: bool,
    risk_level: str,
    source_score: float | None,
) -> float:
    score = 0.0

    if link_active:
        score += 18
    else:
        score -= 35

    if executable:
        score += 20
    else:
        score -= 12

    if explicit_reward:
        score += 18
    else:
        score -= 8

    if reward_amount:
        if reward_amount >= 10_000:
            score += 18
        elif reward_amount >= 1_000:
            score += 14
        elif reward_amount >= 100:
            score += 9
        else:
            score += 4

    if deadline:
        score += 5

    if requirements:
        score += 4

    if capital_required:
        score -= 30

    risk_penalty = {
        "baixo": 0,
        "médio": 8,
        "alto": 22,
        "crítico": 50,
    }
    score -= risk_penalty.get(risk_level, 10)

    if source_score is not None:
        score += max(-5, min(15, source_score / 10))

    return round(max(0, min(100, score)), 2)


def determine_status(
    *,
    link_active: bool,
    executable: bool,
    explicit_reward: bool,
    capital_required: bool,
    risk_level: str,
    deadline: str | None,
    human_approval_required: bool,
) -> tuple[str, str, str]:
    today = datetime.now(timezone.utc).date()

    if deadline:
        try:
            deadline_date = date_parser.parse(deadline).date()
            if deadline_date < today:
                return (
                    "expired",
                    "Descartar como expirada.",
                    "O prazo identificado já terminou.",
                )
        except (ValueError, TypeError):
            pass

    if not link_active:
        return (
            "rejected",
            "Rejeitar ou revisar manualmente o endereço.",
            "O link não respondeu como uma oportunidade ativa.",
        )

    if risk_level == "crítico":
        return (
            "rejected",
            "Rejeitar imediatamente.",
            "Foram encontrados sinais incompatíveis com as políticas de segurança.",
        )

    if capital_required:
        return (
            "approval_required",
            "Solicitar aprovação humana antes de qualquer gasto.",
            "A oportunidade aparenta exigir capital, taxa, depósito ou compra.",
        )

    if executable and explicit_reward and risk_level == "baixo":
        if human_approval_required:
            return (
                "approval_required",
                "Revisar requisitos e autorizar a preparação.",
                "A oportunidade é promissora, mas exige ação humana sensível.",
            )

        return (
            "actionable",
            "Preparar candidatura, proposta ou prova de conceito.",
            "Link ativo, recompensa explícita e baixo risco identificado.",
        )

    if executable:
        return (
            "verified",
            "Realizar revisão humana curta antes da preparação.",
            "A oportunidade parece executável, mas ainda possui informação incompleta.",
        )

    return (
        "rejected",
        "Descartar como conteúdo informativo ou falso positivo.",
        "Não foram encontrados sinais suficientes de uma oportunidade executável.",
    )


def build_query(connection: sqlite3.Connection, limit: int) -> tuple[str, dict[str, str | None]]:
    if not table_exists(connection, "opportunities"):
        raise RuntimeError("Tabela opportunities não existe no banco.")

    columns = get_columns(connection, "opportunities")

    mapping = {
        "id": choose_column(columns, ["id", "opportunity_id", "uuid"]),
        "title": choose_column(columns, ["title", "name", "opportunity_title"]),
        "category": choose_column(columns, ["category", "type", "opportunity_type"]),
        "source": choose_column(columns, ["source", "source_name", "platform"]),
        "url": choose_column(columns, ["url", "html_url", "link", "source_url"]),
        "description": choose_column(
            columns,
            ["description", "body", "summary", "content", "raw_text"],
        ),
        "source_score": choose_column(
            columns,
            ["final_score", "score", "financial_score", "opportunity_score"],
        ),
        "status": choose_column(columns, ["status", "state"]),
        "created_at": choose_column(
            columns,
            ["created_at", "discovered_at", "published_at", "updated_at"],
        ),
    }

    if not mapping["id"]:
        raise RuntimeError("Não foi encontrada coluna identificadora em opportunities.")

    if not mapping["url"]:
        raise RuntimeError("Não foi encontrada coluna de URL em opportunities.")

    def select_expression(alias: str) -> str:
        column = mapping[alias]
        if column:
            return f'o."{column}" AS "{alias}"'
        return f'NULL AS "{alias}"'

    select_fields = ", ".join(
        select_expression(alias)
        for alias in [
            "id",
            "title",
            "category",
            "source",
            "url",
            "description",
            "source_score",
            "status",
            "created_at",
        ]
    )

    order_expression = (
        f'CAST(COALESCE(o."{mapping["source_score"]}", 0) AS REAL) DESC'
        if mapping["source_score"]
        else (
            f'o."{mapping["created_at"]}" DESC'
            if mapping["created_at"]
            else "o.rowid DESC"
        )
    )

    query = f"""
        SELECT {select_fields}
        FROM opportunities o
        LEFT JOIN opportunity_verifications v
          ON CAST(v.opportunity_id AS TEXT) = CAST(o."{mapping['id']}" AS TEXT)
        WHERE v.opportunity_id IS NULL
          AND o."{mapping['url']}" IS NOT NULL
          AND TRIM(CAST(o."{mapping['url']}" AS TEXT)) <> ''
        ORDER BY {order_expression}
        LIMIT ?
    """

    return query, mapping


def verify_opportunity(row: sqlite3.Row, timeout: int) -> VerificationResult:
    opportunity_id = row["id"]
    title = normalize_text(row["title"]) or f"Oportunidade {opportunity_id}"
    category = normalize_text(row["category"]) or "não classificada"
    source = normalize_text(row["source"]) or "desconhecida"
    url = normalize_text(row["url"])
    original_description = normalize_text(row["description"])
    source_score = safe_float(row["source_score"])

    parsed_url = urlparse(url)
    valid_url = parsed_url.scheme in {"http", "https"} and bool(parsed_url.netloc)

    if not valid_url:
        page_status = None
        page_text = ""
        page_title = None
        failure_reason = "URL inválida."
    else:
        page_status, page_text, page_title, failure_reason = fetch_page(url, timeout)

    link_active = page_status is not None and 200 <= page_status < 400
    combined_text = normalize_text(
        " ".join(
            value
            for value in [title, category, source, original_description, page_title, page_text]
            if value
        )
    )
    lowered = combined_text.lower()

    positive_score = sum(
        weight for term, weight in POSITIVE_TERMS.items() if term in lowered
    )
    negative_score = sum(
        weight for term, weight in NEGATIVE_TERMS.items() if term in lowered
    )

    reward_amount, reward_currency, explicit_reward = parse_reward(combined_text)
    deadline = parse_deadline(combined_text)
    requirements = extract_requirements(combined_text)
    country_restrictions = extract_country_restrictions(combined_text)
    payment_method = detect_payment_method(combined_text)

    detected_capital_terms = [term for term in CAPITAL_TERMS if term in lowered]
    capital_required = bool(detected_capital_terms)
    capital_details = (
        ", ".join(detected_capital_terms) if detected_capital_terms else None
    )

    kyc_required = any(term in lowered for term in KYC_TERMS)
    human_approval_required = (
        kyc_required
        or capital_required
        or any(term in lowered for term in HUMAN_APPROVAL_TERMS)
    )

    informational_signals = [
        "news",
        "announcement",
        "article",
        "recap",
        "report",
        "podcast",
    ]
    action_signals = [
        "apply",
        "submit",
        "submission",
        "bounty",
        "reward",
        "prize",
        "grant",
        "proposal",
        "application",
        "issue",
        "hackathon",
        "contest",
        "challenge",
    ]

    executable = (
        link_active
        and positive_score > negative_score
        and any(term in lowered for term in action_signals)
        and not (
            any(term in lowered for term in informational_signals)
            and not explicit_reward
        )
    )

    difficulty, estimated_hours = determine_difficulty(
        combined_text,
        category,
        reward_amount,
    )

    risk_level = calculate_risk(
        combined_text,
        link_active,
        capital_required,
        explicit_reward,
        executable,
    )

    verification_score = calculate_verification_score(
        link_active=link_active,
        executable=executable,
        explicit_reward=explicit_reward,
        reward_amount=reward_amount,
        deadline=deadline,
        requirements=requirements,
        capital_required=capital_required,
        risk_level=risk_level,
        source_score=source_score,
    )

    success_probability = round(
        max(
            0.02,
            min(
                0.90,
                (verification_score / 100)
                * (
                    0.80
                    if difficulty == "alta"
                    else 1.00
                    if difficulty == "média"
                    else 1.10
                ),
            ),
        ),
        3,
    )

    verification_status, recommended_action, recommendation_reason = determine_status(
        link_active=link_active,
        executable=executable,
        explicit_reward=explicit_reward,
        capital_required=capital_required,
        risk_level=risk_level,
        deadline=deadline,
        human_approval_required=human_approval_required,
    )

    if verification_status not in ALLOWED_STATUSES:
        verification_status = "verifying"

    return VerificationResult(
        opportunity_id=opportunity_id,
        title=title,
        category=category,
        source=source,
        url=url,
        http_status=page_status,
        link_active=link_active,
        executable=executable,
        explicit_reward=explicit_reward,
        reward_amount=reward_amount,
        reward_currency=reward_currency,
        deadline=deadline,
        requirements=requirements,
        capital_required=capital_required,
        capital_details=capital_details,
        difficulty=difficulty,
        estimated_hours=estimated_hours,
        risk_level=risk_level,
        success_probability=success_probability,
        country_restrictions=country_restrictions,
        kyc_required=kyc_required,
        human_approval_required=human_approval_required,
        payment_method=payment_method,
        verification_status=verification_status,
        recommended_action=recommended_action,
        recommendation_reason=recommendation_reason,
        verification_score=verification_score,
        verified_at=utc_now(),
        page_title=page_title,
        failure_reason=failure_reason,
    )


def save_result(connection: sqlite3.Connection, result: VerificationResult) -> None:
    raw_json = json.dumps(result.__dict__, ensure_ascii=False, default=str)

    connection.execute(
        """
        INSERT INTO opportunity_verifications (
            opportunity_id,
            title,
            category,
            source,
            url,
            http_status,
            link_active,
            executable,
            explicit_reward,
            reward_amount,
            reward_currency,
            deadline,
            requirements,
            capital_required,
            capital_details,
            difficulty,
            estimated_hours,
            risk_level,
            success_probability,
            country_restrictions,
            kyc_required,
            human_approval_required,
            payment_method,
            verification_status,
            recommended_action,
            recommendation_reason,
            verification_score,
            verified_at,
            page_title,
            failure_reason,
            raw_verification_json
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(opportunity_id) DO UPDATE SET
            title = excluded.title,
            category = excluded.category,
            source = excluded.source,
            url = excluded.url,
            http_status = excluded.http_status,
            link_active = excluded.link_active,
            executable = excluded.executable,
            explicit_reward = excluded.explicit_reward,
            reward_amount = excluded.reward_amount,
            reward_currency = excluded.reward_currency,
            deadline = excluded.deadline,
            requirements = excluded.requirements,
            capital_required = excluded.capital_required,
            capital_details = excluded.capital_details,
            difficulty = excluded.difficulty,
            estimated_hours = excluded.estimated_hours,
            risk_level = excluded.risk_level,
            success_probability = excluded.success_probability,
            country_restrictions = excluded.country_restrictions,
            kyc_required = excluded.kyc_required,
            human_approval_required = excluded.human_approval_required,
            payment_method = excluded.payment_method,
            verification_status = excluded.verification_status,
            recommended_action = excluded.recommended_action,
            recommendation_reason = excluded.recommendation_reason,
            verification_score = excluded.verification_score,
            verified_at = excluded.verified_at,
            page_title = excluded.page_title,
            failure_reason = excluded.failure_reason,
            raw_verification_json = excluded.raw_verification_json
        """,
        (
            str(result.opportunity_id),
            result.title,
            result.category,
            result.source,
            result.url,
            result.http_status,
            int(result.link_active),
            int(result.executable),
            int(result.explicit_reward),
            result.reward_amount,
            result.reward_currency,
            result.deadline,
            result.requirements,
            int(result.capital_required),
            result.capital_details,
            result.difficulty,
            result.estimated_hours,
            result.risk_level,
            result.success_probability,
            result.country_restrictions,
            int(result.kyc_required),
            int(result.human_approval_required),
            result.payment_method,
            result.verification_status,
            result.recommended_action,
            result.recommendation_reason,
            result.verification_score,
            result.verified_at,
            result.page_title,
            result.failure_reason,
            raw_json,
        ),
    )


def generate_outputs(connection: sqlite3.Connection) -> None:
    rows = connection.execute(
        """
        SELECT *
        FROM opportunity_verifications
        ORDER BY
            CASE verification_status
                WHEN 'actionable' THEN 1
                WHEN 'approval_required' THEN 2
                WHEN 'verified' THEN 3
                WHEN 'verifying' THEN 4
                WHEN 'expired' THEN 5
                ELSE 6
            END,
            verification_score DESC,
            success_probability DESC
        """
    ).fetchall()

    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    csv_fields = [
        "opportunity_id",
        "title",
        "category",
        "source",
        "url",
        "reward_amount",
        "reward_currency",
        "deadline",
        "requirements",
        "capital_required",
        "difficulty",
        "estimated_hours",
        "risk_level",
        "success_probability",
        "verification_score",
        "recommended_action",
        "recommendation_reason",
        "verification_status",
        "human_approval_required",
        "country_restrictions",
        "kyc_required",
        "payment_method",
        "link_active",
        "explicit_reward",
        "verified_at",
    ]

    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=csv_fields)
        writer.writeheader()

        for row in rows:
            writer.writerow({field: row[field] for field in csv_fields})

    status_counts = connection.execute(
        """
        SELECT verification_status, COUNT(*) AS total
        FROM opportunity_verifications
        GROUP BY verification_status
        ORDER BY total DESC
        """
    ).fetchall()

    actionable = [
        row
        for row in rows
        if row["verification_status"] in {
            "actionable",
            "approval_required",
            "verified",
        }
    ]

    lines = [
        "# Global Revenue Brain — Oportunidades Verificadas",
        "",
        f"Gerado em: {utc_now()}",
        "",
        "## Resumo",
        "",
        f"- Total verificado: **{len(rows)}**",
        f"- Fila prioritária: **{len(actionable)}**",
    ]

    for status_row in status_counts:
        lines.append(
            f"- {status_row['verification_status']}: **{status_row['total']}**"
        )

    lines.extend(
        [
            "",
            "## Fila prioritária",
            "",
        ]
    )

    if not actionable:
        lines.append("Nenhuma oportunidade suficientemente qualificada nesta execução.")
    else:
        for position, row in enumerate(actionable[:50], start=1):
            reward = "não identificada"

            if row["reward_amount"]:
                reward = (
                    f"{row['reward_currency'] or ''} "
                    f"{row['reward_amount']:,.2f}"
                ).strip()

            probability = (
                f"{float(row['success_probability'] or 0) * 100:.1f}%"
            )

            lines.extend(
                [
                    f"### {position}. {row['title']}",
                    "",
                    f"- Status: **{row['verification_status']}**",
                    f"- Categoria: {row['category']}",
                    f"- Fonte: {row['source']}",
                    f"- URL: {row['url']}",
                    f"- Recompensa: {reward}",
                    f"- Prazo: {row['deadline'] or 'não identificado'}",
                    f"- Capital necessário: {'sim' if row['capital_required'] else 'não identificado'}",
                    f"- Dificuldade: {row['difficulty']}",
                    f"- Tempo estimado: {row['estimated_hours']} horas",
                    f"- Risco: {row['risk_level']}",
                    f"- Probabilidade estimada: {probability}",
                    f"- Score de verificação: {row['verification_score']}/100",
                    f"- KYC: {'sim' if row['kyc_required'] else 'não identificado'}",
                    f"- Aprovação humana: {'sim' if row['human_approval_required'] else 'não'}",
                    f"- Forma de pagamento: {row['payment_method'] or 'não identificada'}",
                    f"- Restrições geográficas: {row['country_restrictions'] or 'não identificadas'}",
                    f"- Requisitos: {row['requirements'] or 'não identificados'}",
                    f"- Próxima ação: **{row['recommended_action']}**",
                    f"- Motivo: {row['recommendation_reason']}",
                    "",
                ]
            )

    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")


def run(limit: int, timeout: int, delay: float) -> int:
    if not DATABASE_PATH.exists():
        log(f"ERRO: banco não encontrado em {DATABASE_PATH}")
        return 1

    connection = connect_database()

    try:
        initialize_schema(connection)
        query, mapping = build_query(connection, limit)

        log(f"Mapeamento da tabela opportunities: {mapping}")

        rows = connection.execute(query, (limit,)).fetchall()

        run_cursor = connection.execute(
            """
            INSERT INTO verification_runs (
                started_at,
                selected_count,
                run_status
            )
            VALUES (?, ?, 'running')
            """,
            (utc_now(), len(rows)),
        )
        run_id = run_cursor.lastrowid
        connection.commit()

        verified_count = 0
        actionable_count = 0
        rejected_count = 0
        error_count = 0

        log(f"{len(rows)} oportunidades selecionadas para verificação.")

        for index, row in enumerate(rows, start=1):
            try:
                log(
                    f"[{index}/{len(rows)}] Verificando: "
                    f"{normalize_text(row['title']) or row['url']}"
                )

                result = verify_opportunity(row, timeout)
                save_result(connection, result)
                connection.commit()

                verified_count += 1

                if result.verification_status in {
                    "actionable",
                    "approval_required",
                    "verified",
                }:
                    actionable_count += 1

                if result.verification_status in {"rejected", "expired"}:
                    rejected_count += 1

                log(
                    f"Status={result.verification_status} | "
                    f"score={result.verification_score} | "
                    f"risco={result.risk_level} | "
                    f"link_ativo={result.link_active}"
                )

            except Exception as exc:
                error_count += 1
                log(f"ERRO ao verificar oportunidade {row['id']}: {exc}")

            if delay > 0:
                time.sleep(delay)

        generate_outputs(connection)

        connection.execute(
            """
            UPDATE verification_runs
            SET
                finished_at = ?,
                verified_count = ?,
                actionable_count = ?,
                rejected_count = ?,
                error_count = ?,
                run_status = ?
            WHERE id = ?
            """,
            (
                utc_now(),
                verified_count,
                actionable_count,
                rejected_count,
                error_count,
                "completed" if error_count == 0 else "completed_with_errors",
                run_id,
            ),
        )
        connection.commit()

        log(
            "Verificação concluída: "
            f"verificadas={verified_count}, "
            f"prioritárias={actionable_count}, "
            f"rejeitadas={rejected_count}, "
            f"erros={error_count}"
        )
        log(f"Relatório: {REPORT_PATH}")
        log(f"CSV: {CSV_PATH}")

        return 0 if verified_count > 0 else 2

    finally:
        connection.close()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Verifica oportunidades já descobertas pelo Global Revenue Brain."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=30,
        help="Quantidade máxima de oportunidades novas a verificar.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help="Timeout HTTP em segundos.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.5,
        help="Intervalo entre requisições.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()

    try:
        exit_code = run(
            limit=max(1, arguments.limit),
            timeout=max(5, arguments.timeout),
            delay=max(0, arguments.delay),
        )
    except KeyboardInterrupt:
        log("Execução interrompida pelo usuário.")
        exit_code = 130
    except Exception as error:
        log(f"ERRO FATAL: {error}")
        exit_code = 1

    sys.exit(exit_code)
