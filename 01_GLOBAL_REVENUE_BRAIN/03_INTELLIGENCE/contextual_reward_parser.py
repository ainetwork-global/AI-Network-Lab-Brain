from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True)
class RewardEvidence:
    amount: float | None
    currency: str | None
    explicit: bool
    confidence: float
    evidence_text: str | None
    rejection_reason: str | None


CURRENCY_PATTERN = (
    r"US\$|USD|USDC|USDT|DAI|R\$|BRL|EUR|€|GBP|£|"
    r"ETH|BTC|SOL|MATIC|AVAX"
)

AMOUNT_PATTERN = r"\d[\d\s.,]*(?:[kKmM])?"

REWARD_CONTEXT_TERMS = {
    "bounty",
    "reward",
    "prize",
    "cash prize",
    "grant amount",
    "grant funding",
    "funding available",
    "compensation",
    "paid task",
    "payment for",
    "payout",
    "winner receives",
    "award amount",
    "total prize pool",
    "remuneration",
    "budget for this task",
    "budget:",
    "reward:",
    "bounty:",
    "prize:",
}

NEGATIVE_CONTEXT_TERMS = {
    "annual recurring revenue",
    "arr",
    "monthly recurring revenue",
    "mrr",
    "valuation",
    "market cap",
    "transaction volume",
    "trading volume",
    "total value locked",
    "tvl",
    "subscription price",
    "pricing plan",
    "monthly plan",
    "per month",
    "/month",
    "api usage",
    "usage limit",
    "credit limit",
    "token supply",
    "gas fee",
    "minimum balance",
    "example",
    "sample",
    "demo",
    "test value",
    "canary",
    "invoice",
    "billing amount",
}

REWARD_PATTERNS = [
    re.compile(
        rf"(?P<context>bounty|reward|prize|grant|compensation|payout|award|budget)"
        rf"[^.\n]{{0,100}}?"
        rf"(?P<currency>{CURRENCY_PATTERN})\s*(?P<amount>{AMOUNT_PATTERN})",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?P<context>bounty|reward|prize|grant|compensation|payout|award|budget)"
        rf"[^.\n]{{0,100}}?"
        rf"(?P<amount>{AMOUNT_PATTERN})\s*(?P<currency>{CURRENCY_PATTERN})",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?P<currency>{CURRENCY_PATTERN})\s*(?P<amount>{AMOUNT_PATTERN})"
        rf"[^.\n]{{0,80}}?"
        rf"(?P<context>bounty|reward|prize|grant|compensation|payout|award)",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?P<amount>{AMOUNT_PATTERN})\s*(?P<currency>{CURRENCY_PATTERN})"
        rf"[^.\n]{{0,80}}?"
        rf"(?P<context>bounty|reward|prize|grant|compensation|payout|award)",
        re.IGNORECASE,
    ),
]

SYMBOL_CURRENCY_MAP = {
    "US$": "USD",
    "$": "USD",
    "USD": "USD",
    "USDC": "USDC",
    "USDT": "USDT",
    "DAI": "DAI",
    "R$": "BRL",
    "BRL": "BRL",
    "€": "EUR",
    "EUR": "EUR",
    "£": "GBP",
    "GBP": "GBP",
    "ETH": "ETH",
    "BTC": "BTC",
    "SOL": "SOL",
    "MATIC": "MATIC",
    "AVAX": "AVAX",
}


def normalize_space(value: str) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def parse_numeric_amount(raw_value: str) -> float | None:
    value = normalize_space(raw_value).replace(" ", "")
    multiplier = 1.0

    if value.lower().endswith("k"):
        multiplier = 1_000.0
        value = value[:-1]
    elif value.lower().endswith("m"):
        multiplier = 1_000_000.0
        value = value[:-1]

    value = re.sub(r"[^\d,.-]", "", value)

    if not value:
        return None

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
        amount = float(value) * multiplier
    except ValueError:
        return None

    if amount <= 0:
        return None

    return amount


def sentence_window(text: str, start: int, end: int, radius: int = 180) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return normalize_space(text[left:right])


def contains_any(text: str, terms: Iterable[str]) -> bool:
    lowered = text.lower()
    return any(term in lowered for term in terms)


def score_candidate(context: str, amount: float, currency: str) -> tuple[float, list[str]]:
    lowered = context.lower()
    score = 0.0
    reasons: list[str] = []

    positive_matches = [
        term for term in REWARD_CONTEXT_TERMS
        if term in lowered
    ]

    negative_matches = [
        term for term in NEGATIVE_CONTEXT_TERMS
        if term in lowered
    ]

    if positive_matches:
        score += min(0.70, 0.32 + len(positive_matches) * 0.10)
        reasons.append("contexto financeiro de recompensa identificado")

    if re.search(
        r"(apply|submit|complete|solve|winner|selected|eligible|deadline)",
        lowered,
    ):
        score += 0.12
        reasons.append("ação executável identificada")

    if re.search(
        r"(will receive|receives|paid upon|payout of|award of|up to)",
        lowered,
    ):
        score += 0.18
        reasons.append("linguagem explícita de pagamento identificada")

    if negative_matches:
        score -= min(0.75, len(negative_matches) * 0.20)
        reasons.append(
            "contexto negativo: " + ", ".join(sorted(set(negative_matches)))
        )

    if amount >= 100_000_000:
        score -= 0.55
        reasons.append("valor extremo provavelmente não é recompensa individual")
    elif amount >= 10_000_000:
        score -= 0.35
        reasons.append("valor muito alto exige forte evidência")
    elif amount < 0.01:
        score -= 0.30
        reasons.append("valor insignificante")
    elif amount <= 0.10:
        score -= 0.12
        reasons.append("valor muito baixo, possivelmente teste")

    if currency in {"ETH", "BTC", "SOL", "MATIC", "AVAX"}:
        score -= 0.05
        reasons.append("criptoativo exige confirmação adicional")

    return max(0.0, min(1.0, score)), reasons


def parse_contextual_reward(text: str) -> RewardEvidence:
    normalized = normalize_space(text)

    if not normalized:
        return RewardEvidence(
            amount=None,
            currency=None,
            explicit=False,
            confidence=0.0,
            evidence_text=None,
            rejection_reason="texto vazio",
        )

    candidates: list[tuple[float, float, str, str, list[str]]] = []

    for pattern in REWARD_PATTERNS:
        for match in pattern.finditer(normalized):
            amount = parse_numeric_amount(match.group("amount"))
            currency_raw = match.group("currency").upper()
            currency = SYMBOL_CURRENCY_MAP.get(currency_raw, currency_raw)

            if amount is None:
                continue

            context = sentence_window(
                normalized,
                match.start(),
                match.end(),
            )

            confidence, reasons = score_candidate(
                context,
                amount,
                currency,
            )

            candidates.append(
                (
                    confidence,
                    amount,
                    currency,
                    context,
                    reasons,
                )
            )

    if not candidates:
        return RewardEvidence(
            amount=None,
            currency=None,
            explicit=False,
            confidence=0.0,
            evidence_text=None,
            rejection_reason=(
                "nenhum valor monetário acompanhado de contexto explícito "
                "de bounty, reward, prize, grant ou pagamento"
            ),
        )

    candidates.sort(
        key=lambda candidate: (
            candidate[0],
            candidate[1],
        ),
        reverse=True,
    )

    confidence, amount, currency, context, reasons = candidates[0]

    if confidence < 0.40:
        return RewardEvidence(
            amount=None,
            currency=None,
            explicit=False,
            confidence=round(confidence, 3),
            evidence_text=context[:500],
            rejection_reason="; ".join(reasons) or "evidência contextual insuficiente",
        )

    return RewardEvidence(
        amount=amount,
        currency=currency,
        explicit=True,
        confidence=round(confidence, 3),
        evidence_text=context[:500],
        rejection_reason=None,
    )


def parse_reward(text: str) -> tuple[float | None, str | None, bool]:
    evidence = parse_contextual_reward(text)

    return (
        evidence.amount,
        evidence.currency,
        evidence.explicit,
    )
