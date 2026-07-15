from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = PROJECT_ROOT / "01_CONFIG" / "hunter_sources.json"

MONEY_PATTERNS = [
    re.compile(
        r"(?:US\$|\$|USD\s*)\s*([0-9][0-9,]*(?:\.[0-9]{1,2})?)",
        re.IGNORECASE,
    ),
    re.compile(
        r"([0-9][0-9,]*(?:\.[0-9]{1,2})?)\s*(?:USD|USDC)",
        re.IGNORECASE,
    ),
]


def load_config() -> dict[str, Any]:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8-sig"))


def extract_estimated_value(text: str) -> float | None:
    values: list[float] = []

    for pattern in MONEY_PATTERNS:
        for match in pattern.finditer(text):
            raw = match.group(1).replace(",", "")

            try:
                value = float(raw)
            except ValueError:
                continue

            if 0 < value <= 10_000_000:
                values.append(value)

    return max(values) if values else None


def score_opportunity(
    title: str,
    description: str,
    category: str,
    source_type: str,
    source_url: str,
) -> dict[str, Any]:
    config = load_config()
    text = f"{title} {description}".lower()

    financial_score = 0.0
    confidence_score = 25.0
    automation_score = 20.0
    risk_score = 0.0
    reasons: list[str] = []

    for keyword, weight in config["positive_keywords"].items():
        if keyword.lower() in text:
            financial_score += float(weight)
            reasons.append(f"+{weight} palavra positiva: {keyword}")

    for keyword, weight in config["negative_keywords"].items():
        if keyword.lower() in text:
            risk_score += abs(float(weight))
            reasons.append(f"{weight} sinal de risco: {keyword}")

    estimated_value = extract_estimated_value(text)

    if estimated_value is not None:
        confidence_score += 20
        reasons.append(f"valor financeiro detectado: USD {estimated_value:.2f}")

        if estimated_value >= 10_000:
            financial_score += 30
        elif estimated_value >= 1_000:
            financial_score += 22
        elif estimated_value >= 100:
            financial_score += 15
        elif estimated_value > 0:
            financial_score += 8

    category_bonus = {
        "open_source_bounty": 20,
        "paid_development": 18,
        "bug_bounty": 18,
        "grant": 16,
        "web3_grant": 14,
        "crypto_bounty": 14,
        "ai_bounty": 18,
        "ai_integration": 18,
        "hackathon": 12,
        "competition": 10,
        "open_source": 3,
    }.get(category, 0)

    financial_score += category_bonus

    if category_bonus:
        reasons.append(f"+{category_bonus} categoria: {category}")

    if source_type == "github_api":
        confidence_score += 15
        automation_score += 20
        reasons.append("+15 fonte estruturada GitHub")
        reasons.append("+20 análise automatizável")

    if source_url.startswith("https://"):
        confidence_score += 5

    if "apply" in text or "submit" in text:
        automation_score += 10

    if "deadline" in text:
        confidence_score += 5

    if "entry fee" in text or "deposit" in text:
        risk_score += 25

    financial_score = min(financial_score, 100)
    confidence_score = min(confidence_score, 100)
    automation_score = min(automation_score, 100)
    risk_score = min(risk_score, 100)

    final_score = (
        financial_score * 0.45
        + confidence_score * 0.30
        + automation_score * 0.25
        - risk_score * 0.50
    )

    final_score = max(0.0, min(round(final_score, 2), 100.0))

    return {
        "estimated_value": estimated_value,
        "financial_score": round(financial_score, 2),
        "confidence_score": round(confidence_score, 2),
        "automation_score": round(automation_score, 2),
        "risk_score": round(risk_score, 2),
        "final_score": final_score,
        "score_reason": " | ".join(reasons[:20]),
    }
