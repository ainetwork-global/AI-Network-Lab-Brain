from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RiskDecision:
    level: str
    decision: str
    reasons: tuple[str, ...]


PROHIBITED = {
    "fraud_or_fake_identity": ("fake account", "conta falsa", "impersonat", "identity fraud"),
    "unauthorized_intrusion": ("unauthorized access", "hack any target", "invasão não autorizada"),
    "terms_evasion": ("bypass terms", "evade terms", "evasão de termos", "ban evasion"),
    "market_manipulation": ("wash trading", "market manipulation", "manipulação de mercado"),
    "artificial_engagement": ("fake review", "fake followers", "artificial engagement", "engajamento artificial"),
}

RED = {
    "upfront_spend": ("entry fee", "registration fee", "deposit required", "purchase required", "paid subscription", "taxa de inscrição", "depósito", "compra obrigatória"),
    "wallet_or_funds": ("private key", "seed phrase", "wallet signature", "sign transaction", "funded wallet", "chave privada", "assinar transação"),
    "sensitive_credentials": ("share password", "send password", "api secret", "expose token", "compartilhe sua senha"),
    "legal_or_financial_commitment": ("binding contract", "personal guarantee", "loan", "credit application", "contrato vinculante", "empréstimo"),
}

YELLOW = {
    "public_representation": ("post publicly", "publish", "submit", "application", "comment to claim", "pull request", "publicar", "candidatura"),
    "identity_or_kyc": ("kyc", "identity verification", "government id", "biometric", "reconhecimento facial"),
    "security_testing": ("bug bounty", "penetration test", "vulnerability", "security research"),
    "personal_data": ("personal data", "phone number", "home address", "tax id", "dados pessoais", "endereço residencial"),
}

UNKNOWN_MARKERS = ("unknown", "not confirmed", "manual review", "unverified", "não confirmado", "não verificado")


def _text(row: dict[str, object]) -> str:
    return " ".join(str(value or "") for value in row.values()).lower()


def _matches(text: str, rules: dict[str, tuple[str, ...]]) -> list[str]:
    return [name for name, terms in rules.items() if any(term in text for term in terms)]


def assess(row: dict[str, object], action: str = "internal_development") -> RiskDecision:
    text = _text(row)
    prohibited = _matches(text, PROHIBITED)
    if prohibited:
        return RiskDecision("PROHIBITED", "REJECT", tuple(prohibited))

    red = _matches(text, RED)
    if red:
        return RiskDecision("RED", "HUMAN_APPROVAL_REQUIRED", tuple(red))

    yellow_rules = dict(YELLOW)
    if action == "internal_development":
        yellow_rules.pop("public_representation", None)
    yellow = _matches(text, yellow_rules)
    if any(marker in text for marker in UNKNOWN_MARKERS):
        yellow.append("material_information_unverified")

    eligibility = str(row.get("eligibility_status") or row.get("international_eligibility") or "").lower()
    if eligibility and not re.search(r"allowed|eligible|confirmed|brasil|brazil", eligibility):
        yellow.append("brazilian_eligibility_not_confirmed")

    if yellow:
        return RiskDecision("YELLOW", "HUMAN_APPROVAL_REQUIRED", tuple(dict.fromkeys(yellow)))

    return RiskDecision("GREEN", "AUTONOMOUS_INTERNAL_EXECUTION", ("verified_low_risk_internal_work",))
