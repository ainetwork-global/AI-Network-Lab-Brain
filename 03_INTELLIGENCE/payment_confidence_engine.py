from __future__ import annotations

import csv
import json
import math
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
OPPORTUNITY_DIR = ROOT / "01_GLOBAL_REVENUE_BRAIN" / "04_OPPORTUNITIES"
REPORT_DIR = ROOT / "01_GLOBAL_REVENUE_BRAIN" / "12_REPORTS"
EXECUTION_DIR = ROOT / "01_GLOBAL_REVENUE_BRAIN" / "05_EXECUTION"

OUTPUT_RANKING = OPPORTUNITY_DIR / "payment_confidence_ranking.csv"
OUTPUT_APPROVED = OPPORTUNITY_DIR / "payment_verified_execution_candidates.csv"
OUTPUT_REJECTED = OPPORTUNITY_DIR / "payment_confidence_rejected.csv"
OUTPUT_REPORT = REPORT_DIR / "LATEST_PAYMENT_CONFIDENCE_REPORT.md"
OUTPUT_TARGET = ROOT / "01_GLOBAL_REVENUE_BRAIN" / "00_CURRENT_STATE" / "CURRENT_BEST_TARGET.md"
OUTPUT_HANDOFF = EXECUTION_DIR / "NEXT_PAYMENT_EXECUTION.json"

MIN_CONFIDENCE = 80.0
AUTO_START_CONFIDENCE = 85.0
MIN_REWARD_USD = 25.0
MIN_REVENUE_PER_HOUR = 10.0

REJECTED_SOURCE_FILE = (
    ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
    / "06_REJECTIONS"
    / "rejected_source_repositories.csv"
)

MIRROR_SIGNAL_PATTERNS = (
    r"\bsource url\b",
    r"\boriginal issue\b",
    r"\boriginal bounty\b",
    r"\bmirrored from\b",
    r"\bimported from\b",
    r"\baggregated from\b",
)

def load_rejected_source_repositories() -> set[str]:
    rejected: set[str] = set()

    if not REJECTED_SOURCE_FILE.exists():
        return rejected

    try:
        with REJECTED_SOURCE_FILE.open(
            "r",
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            for row in csv.DictReader(handle):
                repository = str(row.get("repository", "")).strip().lower()

                if repository:
                    rejected.add(repository)
    except Exception as exc:
        print(
            f"[WARN] Falha ao carregar fontes rejeitadas: {exc}",
            file=sys.stderr,
        )

    return rejected
CSV_PRIORITY = [
    "execution_candidate_ranking.csv",
    "payment_probability_ranking.csv",
    "DISCOVERY_PROMOTED_QUEUE.csv",
    "verified_opportunities.csv",
    "ranked_opportunities.csv",
    "execution_tasks.csv",
]

BAD_TEXT = (
    "best submission wins",
    "winning submission",
    "one winning submission",
    "contest",
    "competition",
    "hackathon prize",
    "research proposal",
    "research packet",
    "collect and compare",
    "idea submission",
    "grant application",
    "request for proposal",
    "payment details will be handled privately",
    "may reject submissions",
    "no guaranteed payment",
)

GOOD_TECH = (
    "bug",
    "fix",
    "implement",
    "implementation",
    "feature",
    "integration",
    "api",
    "sdk",
    "test",
    "typescript",
    "python",
    "javascript",
    "rust",
    "golang",
    "solidity",
    "documentation",
    "refactor",
    "migration",
    "cli",
    "plugin",
    "mcp",
)

PAYMENT_TERMS = (
    "bounty",
    "reward",
    "payout",
    "prize",
    "paid to contributor",
    "paid to the contributor",
    "payment to contributor",
    "payment to the contributor",
    "reward for accepted pull request",
    "reward for an accepted pull request",
    "reward for accepted submission",
    "payment after acceptance",
)

EXECUTOR_PAYMENT_PATTERNS = (
    r"\bbounty\b.{0,100}(?:usd|usdc|usdt|\$|€|eur)\s*[0-9]",
    r"(?:usd|usdc|usdt|\$|€|eur)\s*[0-9][0-9,]*(?:\.[0-9]+)?.{0,100}\bbounty\b",
    r"\breward\b.{0,100}(?:usd|usdc|usdt|\$|€|eur)\s*[0-9]",
    r"(?:usd|usdc|usdt|\$|€|eur)\s*[0-9][0-9,]*(?:\.[0-9]+)?.{0,100}\breward\b",
    r"\bpayout\b.{0,100}(?:usd|usdc|usdt|\$|€|eur)\s*[0-9]",
    r"\bpaid to (?:the )?(?:developer|contributor|submitter|winner)\b",
    r"\bpayment (?:to|for) (?:the )?(?:developer|contributor|submitter|winner)\b",
    r"\breward for (?:an? )?(?:accepted|merged) (?:pull request|pr|submission|solution)\b",
)

COMMERCIAL_PRICING_PATTERNS = (
    r"\bonboarding\b",
    r"\bsubscription\b",
    r"\bmonthly\b",
    r"\bper month\b",
    r"/month\b",
    r"\bbilling cycle\b",
    r"\bpricing plan\b",
    r"\bmerchant\b",
    r"\bcustomer pays\b",
    r"\bclient pays\b",
    r"\bimplementation fee\b",
    r"\bsubscription fee\b",
    r"\bcommercial terms\b",
    r"\bproposal pricing\b",
    r"\bthird-party vendor fees\b",
)

TRUSTED_PAYMENT_SOURCES = (
    "algora",
    "polar",
    "gitcoin",
    "immunefi",
    "hackerone",
    "bugcrowd",
    "code4rena",
    "sherlock",
    "cantina",
    "issuehunt",
    "bountysource",
)

CONCURRENCY_TERMS = (
    "claimed",
    "assigned",
    "in progress",
    "working on this",
    "/attempt",
    "/claim",
    "pull request submitted",
    "pr submitted",
)


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


def normalized_row(row: dict[str, Any]) -> dict[str, str]:
    return {
        normalize_key(str(key)): "" if value is None else str(value).strip()
        for key, value in row.items()
    }


def first_value(row: dict[str, str], names: list[str]) -> str:
    for name in names:
        value = row.get(normalize_key(name), "").strip()
        if value:
            return value
    return ""


def joined_text(row: dict[str, str]) -> str:
    return " ".join(str(value) for value in row.values()).lower()


def parse_number(value: str) -> float | None:
    if not value:
        return None

    cleaned = value.lower().strip()
    cleaned = cleaned.replace("usd", "").replace("usdc", "").replace("usdt", "")
    cleaned = cleaned.replace("eur", "").replace("gbp", "")
    cleaned = cleaned.replace("$", "").replace("€", "").replace("£", "")
    cleaned = cleaned.replace(",", "").replace("_", "").strip()

    multiplier = 1.0
    if cleaned.endswith("k"):
        multiplier = 1000.0
        cleaned = cleaned[:-1]
    elif cleaned.endswith("m"):
        multiplier = 1_000_000.0
        cleaned = cleaned[:-1]

    match = re.search(r"-?\d+(?:\.\d+)?", cleaned)
    if not match:
        return None

    try:
        return float(match.group(0)) * multiplier
    except ValueError:
        return None


def extract_reward(row: dict[str, str]) -> float | None:
    candidates = [
        "reward_amount",
        "reward",
        "amount_usd",
        "reward_usd",
        "bounty_usd",
        "bounty_amount",
        "prize",
        "value",
        "amount",
        "expected_reward",
        "reward_pool",
    ]

    for key in candidates:
        parsed = parse_number(first_value(row, [key]))
        if parsed is not None and parsed > 0:
            return parsed

    text = joined_text(row)
    matches = re.findall(
        r"(?:usd|usdc|usdt|\$|€|eur)\s*([0-9][0-9,]*(?:\.\d+)?\s*[km]?)",
        text,
        flags=re.IGNORECASE,
    )

    amounts = [parse_number(match) for match in matches]
    amounts = [amount for amount in amounts if amount and amount > 0]
    return max(amounts) if amounts else None


def extract_repository(row: dict[str, str]) -> str:
    direct = first_value(
        row,
        [
            "repository",
            "repo",
            "github_repository",
            "full_name",
            "repository_name",
            "project",
        ],
    )

    if re.fullmatch(r"[\w.-]+/[\w.-]+", direct):
        return direct

    urls = [
        first_value(row, ["url"]),
        first_value(row, ["issue_url"]),
        first_value(row, ["source_url"]),
        first_value(row, ["html_url"]),
    ]

    for url in urls:
        match = re.search(r"github\.com/([^/\s]+)/([^/#?\s]+)", url)
        if match:
            return f"{match.group(1)}/{match.group(2).removesuffix('.git')}"

    text = joined_text(row)
    match = re.search(r"github\.com/([^/\s]+)/([^/#?\s]+)", text)
    if match:
        return f"{match.group(1)}/{match.group(2).removesuffix('.git')}"

    return ""


def extract_issue_number(row: dict[str, str]) -> str:
    direct = first_value(
        row,
        ["issue_number", "issue", "number", "github_issue", "ticket_number"],
    )

    match = re.search(r"\d+", direct)
    if match:
        return match.group(0)

    for key in ["issue_url", "url", "source_url", "html_url"]:
        value = first_value(row, [key])
        match = re.search(r"/issues/(\d+)", value)
        if match:
            return match.group(1)

    return ""


def extract_url(row: dict[str, str]) -> str:
    return first_value(
        row,
        ["issue_url", "url", "source_url", "html_url", "opportunity_url"],
    )


def get_existing_score(row: dict[str, str]) -> float:
    for key in [
        "adaptive_score",
        "execution_score",
        "score",
        "ranking_score",
        "final_score",
        "confidence_score",
        "payment_probability",
    ]:
        parsed = parse_number(first_value(row, [key]))
        if parsed is not None:
            return max(0.0, min(parsed, 100.0))
    return 50.0


def score_candidate(row: dict[str, str], source_file: str) -> dict[str, Any]:
    text = joined_text(row)
    reward = extract_reward(row)

    mirror_signal_count = sum(
        1
        for pattern in MIRROR_SIGNAL_PATTERNS
        if re.search(pattern, text, flags=re.IGNORECASE)
    )

    mirror_signal_count = sum(
        1
        for pattern in MIRROR_SIGNAL_PATTERNS
        if re.search(pattern, text, flags=re.IGNORECASE)
    )
    repository = extract_repository(row)
    issue_number = extract_issue_number(row)
    url = extract_url(row)
    source_name = first_value(
        row,
        ["source_name", "source", "platform", "origin", "provider"],
    )
    title = first_value(
        row,
        ["title", "name", "opportunity", "task_title", "issue_title"],
    )
    status = first_value(row, ["status", "state", "task_status"]).lower()
    existing_score = get_existing_score(row)

    reasons: list[str] = []
    penalties: list[str] = []
    hard_rejections: list[str] = []

    live_competition_level = first_value(
        row,
        ["competition_level_live"],
    ).strip().upper()

    live_competition_score = parse_number(
        first_value(
            row,
            ["competition_score_live"],
        )
    )

    live_attempts = parse_number(
        first_value(
            row,
            [
                "attempts",
                "attempt_count",
                "live_attempts",
            ],
        )
    ) or 0.0

    live_pull_requests = parse_number(
        first_value(
            row,
            [
                "pull_requests",
                "pr_count",
                "live_pull_requests",
            ],
        )
    ) or 0.0

    if live_competition_level:
        reasons.append(
            f"concorrência ao vivo verificada: "
            f"{live_competition_level}"
        )

        if live_competition_level != "LOW":
            hard_rejections.append(
                "concorrência ao vivo acima de LOW: "
                f"{live_competition_level}"
            )

    if (
        live_competition_score is not None
        and live_competition_score >= 10
    ):
        hard_rejections.append(
            "score de concorrência ao vivo acima do limite: "
            f"{live_competition_score:.2f}"
        )

    if live_attempts >= 2:
        hard_rejections.append(
            "duas ou mais tentativas ao vivo detectadas: "
            f"{live_attempts:.0f}"
        )

    if live_pull_requests >= 2:
        hard_rejections.append(
            "dois ou mais pull requests concorrentes detectados: "
            f"{live_pull_requests:.0f}"
        )

    payment_evidence = 0.0
    platform_trust = 0.0
    clarity = 0.0
    technical_fit = 0.0
    competition = 0.0
    activity = 0.0
    roi = 0.0

    executor_payment_matches = [
        pattern
        for pattern in EXECUTOR_PAYMENT_PATTERNS
        if re.search(pattern, text, flags=re.IGNORECASE | re.DOTALL)
    ]

    commercial_pricing_matches = [
        pattern
        for pattern in COMMERCIAL_PRICING_PATTERNS
        if re.search(pattern, text, flags=re.IGNORECASE)
    ]

    trusted_source_signal = any(
        source in text or source in source_name.lower() or source in url.lower()
        for source in TRUSTED_PAYMENT_SOURCES
    )

    explicit_executor_payment = bool(executor_payment_matches)
    commercial_pricing_risk = len(commercial_pricing_matches) >= 2

    if reward is not None and explicit_executor_payment:
        payment_evidence += 22
        reasons.append(f"recompensa ao executor explicitamente associada: {reward:.2f}")

        if reward >= 100:
            payment_evidence += 4

        if reward >= 500:
            payment_evidence += 3
    elif reward is not None and trusted_source_signal:
        payment_evidence += 15
        reasons.append(
            f"valor monetário em plataforma de bounty reconhecida: {reward:.2f}"
        )
    elif reward is not None:
        hard_rejections.append(
            "valor monetário encontrado, mas não está explicitamente associado "
            "ao pagamento do executor"
        )
    else:
        hard_rejections.append("sem recompensa monetária identificável")

    if commercial_pricing_risk and not explicit_executor_payment:
        hard_rejections.append(
            "valores aparentam ser preços comerciais, assinatura, onboarding "
            "ou cobrança ao cliente"
        )

    if any(term in text for term in PAYMENT_TERMS):
        payment_evidence += 5
    else:
        penalties.append("texto sem termos claros de pagamento ao executor")

    trusted_match = next(
        (
            source
            for source in TRUSTED_PAYMENT_SOURCES
            if source in text or source in source_name.lower() or source in url.lower()
        ),
        None,
    )

    if trusted_match:
        platform_trust = 20
        reasons.append(f"plataforma de pagamento reconhecida: {trusted_match}")
    elif "github.com" in url.lower() or repository:
        platform_trust = 6
        penalties.append("GitHub isolado, sem intermediador de pagamento comprovado")
    else:
        platform_trust = 3

    if mirror_signal_count >= 2:
        hard_rejections.append(
            "oportunidade aparenta ser espelho ou agregação de fonte externa"
        )

    if mirror_signal_count >= 2:
        hard_rejections.append(
            "oportunidade aparenta ser espelho ou agregação de fonte externa"
        )

    bad_matches = [term for term in BAD_TEXT if term in text]
    if bad_matches:
        hard_rejections.append(
            "formato subjetivo/competitivo: " + ", ".join(bad_matches[:3])
        )

    technical_matches = [term for term in GOOD_TECH if term in text]
    technical_fit = min(18.0, 4.0 + len(set(technical_matches)) * 2.0)

    if technical_matches:
        reasons.append(
            "trabalho técnico: " + ", ".join(sorted(set(technical_matches))[:5])
        )
    else:
        technical_fit = 0
        hard_rejections.append("trabalho técnico executável não identificado")

    if repository and issue_number:
        clarity += 12
        reasons.append("repositório e issue identificados")
    elif repository:
        clarity += 5
        penalties.append("repositório identificado, mas issue ausente")
    else:
        hard_rejections.append("repositório não identificado")

    if status in {"closed", "completed", "paid", "cancelled", "canceled"}:
        hard_rejections.append(f"oportunidade não está aberta: {status}")
    elif status in {"open", "pending", "ready", "approved", "verified"}:
        activity += 6

    comments = parse_number(
        first_value(row, ["comments", "comment_count", "comments_count"])
    )
    attempts = parse_number(
        first_value(
            row,
            [
                "attempts",
                "claim_count",
                "competitors",
                "competition_count",
                "pull_requests",
                "pr_count",
            ],
        )
    )

    concurrency_signals = sum(text.count(term) for term in CONCURRENCY_TERMS)
    observed_competition = max(
        attempts or 0,
        comments or 0,
        float(concurrency_signals),
    )

    if observed_competition <= 1:
        competition = 15
        reasons.append("concorrência aparente baixa")
    elif observed_competition <= 4:
        competition = 10
    elif observed_competition <= 10:
        competition = 5
        penalties.append("concorrência moderada")
    else:
        competition = 0
        penalties.append(f"concorrência elevada: sinal {observed_competition:.0f}")

    estimated_hours = parse_number(
        first_value(
            row,
            [
                "estimated_hours",
                "hours",
                "effort_hours",
                "estimated_effort_hours",
            ],
        )
    )

    if estimated_hours is None:
        estimated_hours = 12.0

    if reward is not None and estimated_hours > 0:
        revenue_per_hour = reward / estimated_hours

        if reward < MIN_REWARD_USD:
            hard_rejections.append(
                f"recompensa abaixo do mínimo econômico: "
                f"{reward:.2f} < {MIN_REWARD_USD:.2f}"
            )

        if revenue_per_hour < MIN_REVENUE_PER_HOUR:
            hard_rejections.append(
                f"retorno por hora abaixo do mínimo econômico: "
                f"{revenue_per_hour:.2f} < "
                f"{MIN_REVENUE_PER_HOUR:.2f}"
            )

        if revenue_per_hour >= 100:
            roi = 12
        elif revenue_per_hour >= 50:
            roi = 10
        elif revenue_per_hour >= 25:
            roi = 8
        elif revenue_per_hour >= 10:
            roi = 5
        else:
            roi = 0
            penalties.append("retorno por hora economicamente inviável")
    else:
        revenue_per_hour = 0.0
        hard_rejections.append(
            "não foi possível calcular retorno econômico por hora"
        )

    activity += min(5.0, existing_score / 20.0)

    raw_score = (
        payment_evidence
        + platform_trust
        + clarity
        + technical_fit
        + competition
        + activity
        + roi
    )

    if hard_rejections:
        raw_score = min(raw_score, 49.0)

    final_score = max(0.0, min(round(raw_score, 2), 100.0))

    if hard_rejections:
        decision = "REJECTED"
    elif final_score >= AUTO_START_CONFIDENCE:
        decision = "AUTO_START_LOCAL_EXECUTION"
    elif final_score >= MIN_CONFIDENCE:
        decision = "PAYMENT_VERIFIED_CANDIDATE"
    else:
        decision = "OBSERVE"

    normalized = dict(row)

    return {
        **normalized,
        "_source_file": source_file,
        "normalized_title": title,
        "normalized_repository": repository,
        "normalized_issue_number": issue_number,
        "normalized_url": url,
        "normalized_source_name": source_name,
        "reward_usd": round(reward or 0.0, 2),
        "estimated_hours": round(estimated_hours, 2),
        "estimated_revenue_per_hour": round(revenue_per_hour, 2),
        "payment_evidence_score": round(payment_evidence, 2),
        "platform_trust_score": round(platform_trust, 2),
        "clarity_score": round(clarity, 2),
        "technical_fit_score": round(technical_fit, 2),
        "competition_score": round(competition, 2),
        "activity_score": round(activity, 2),
        "roi_score": round(roi, 2),
        "payment_confidence_score": final_score,
        "payment_decision": decision,
        "positive_evidence": " | ".join(reasons),
        "risk_evidence": " | ".join(penalties),
        "hard_rejection_reasons": " | ".join(hard_rejections),
    }


def load_candidates() -> list[tuple[dict[str, str], str]]:
    candidates: list[tuple[dict[str, str], str]] = []
    rejected_sources = load_rejected_source_repositories()
    rejected_sources = load_rejected_source_repositories()
    visited: set[Path] = set()

    ordered_files: list[Path] = []

    for filename in CSV_PRIORITY:
        path = OPPORTUNITY_DIR / filename
        if path.exists():
            ordered_files.append(path)

    for path in sorted(OPPORTUNITY_DIR.rglob("*.csv")):
        if path.name in {
            OUTPUT_RANKING.name,
            OUTPUT_APPROVED.name,
            OUTPUT_REJECTED.name,
        }:
            continue
        if path not in ordered_files:
            ordered_files.append(path)

    for path in ordered_files:
        resolved = path.resolve()
        if resolved in visited:
            continue
        visited.add(resolved)

        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)

                if not reader.fieldnames:
                    continue

                for raw in reader:
                    row = normalized_row(raw)

                    if not any(row.values()):
                        continue

                    repository = extract_repository(row).lower()

                    if repository and repository in rejected_sources:
                        continue

                    repository = extract_repository(row).lower()

                    if repository and repository in rejected_sources:
                        continue

                    candidates.append((row, str(path.relative_to(ROOT))))
        except Exception as exc:
            print(f"[WARN] Falha ao ler {path}: {exc}", file=sys.stderr)

    false_positive_path = (
        ROOT
        / "01_GLOBAL_REVENUE_BRAIN"
        / "06_REJECTIONS"
        / "payment_false_positives.csv"
    )

    if false_positive_path.exists():
        rejected_keys: set[str] = set()

        try:
            with false_positive_path.open(
                "r",
                encoding="utf-8-sig",
                newline="",
            ) as handle:
                for rejected in csv.DictReader(handle):
                    repository = str(rejected.get("repository", "")).lower().strip()
                    issue = str(rejected.get("issue_number", "")).strip()

                    if repository and issue:
                        rejected_keys.add(f"{repository}#{issue}")
        except Exception as exc:
            print(
                f"[WARN] Falha ao carregar falsos positivos: {exc}",
                file=sys.stderr,
            )

        filtered: list[tuple[dict[str, str], str]] = []

        for row, source_file in candidates:
            repository = extract_repository(row).lower()
            issue = extract_issue_number(row)

            if repository and issue and f"{repository}#{issue}" in rejected_keys:
                continue

            filtered.append((row, source_file))

        candidates = filtered

    return candidates


def deduplicate(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: dict[str, dict[str, Any]] = {}

    for record in records:
        repository = record.get("normalized_repository", "")
        issue = record.get("normalized_issue_number", "")
        url = record.get("normalized_url", "")
        title = record.get("normalized_title", "")

        key = (
            f"{repository.lower()}#{issue}"
            if repository and issue
            else url.lower() or title.lower()
        )

        if not key:
            key = json.dumps(record, sort_keys=True, ensure_ascii=False)

        current = selected.get(key)

        if (
            current is None
            or float(record["payment_confidence_score"])
            > float(current["payment_confidence_score"])
        ):
            selected[key] = record

    return list(selected.values())


def write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    if not records:
        path.write_text("", encoding="utf-8")
        return

    fields: list[str] = []
    seen: set[str] = set()

    priority = [
        "payment_confidence_score",
        "payment_decision",
        "normalized_repository",
        "normalized_issue_number",
        "normalized_title",
        "reward_usd",
        "estimated_hours",
        "estimated_revenue_per_hour",
        "normalized_source_name",
        "normalized_url",
        "positive_evidence",
        "risk_evidence",
        "hard_rejection_reasons",
        "_source_file",
    ]

    for field in priority:
        if any(field in record for record in records):
            fields.append(field)
            seen.add(field)

    for record in records:
        for field in record:
            if field not in seen:
                fields.append(field)
                seen.add(field)

    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(records)


def write_report(
    ranked: list[dict[str, Any]],
    approved: list[dict[str, Any]],
    rejected: list[dict[str, Any]],
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    auto = [
        record
        for record in approved
        if record["payment_decision"] == "AUTO_START_LOCAL_EXECUTION"
    ]

    lines = [
        "# Latest Payment Confidence Report",
        "",
        f"- Generated at: `{now}`",
        f"- Unique candidates analyzed: **{len(ranked)}**",
        f"- Payment-verified candidates: **{len(approved)}**",
        f"- Auto-start candidates: **{len(auto)}**",
        f"- Rejected candidates: **{len(rejected)}**",
        f"- Minimum confidence: **{MIN_CONFIDENCE:.0f}**",
        f"- Local auto-start threshold: **{AUTO_START_CONFIDENCE:.0f}**",
        "",
        "## Ranking",
        "",
        "| Rank | Confidence | Decision | Reward | Repository | Issue | Title |",
        "|---:|---:|---|---:|---|---:|---|",
    ]

    for index, record in enumerate(ranked[:25], 1):
        title = str(record.get("normalized_title", "")).replace("|", "/")
        repository = str(record.get("normalized_repository", "")).replace("|", "/")
        issue = str(record.get("normalized_issue_number", ""))
        lines.append(
            f"| {index} | {record['payment_confidence_score']:.2f} | "
            f"{record['payment_decision']} | "
            f"${record['reward_usd']:.2f} | {repository} | {issue} | {title} |"
        )

    if approved:
        best = approved[0]
        lines.extend(
            [
                "",
                "## Current Best Target",
                "",
                f"- Repository: `{best.get('normalized_repository', '')}`",
                f"- Issue: `{best.get('normalized_issue_number', '')}`",
                f"- Reward: `${best.get('reward_usd', 0):.2f}`",
                f"- Confidence: `{best.get('payment_confidence_score', 0):.2f}`",
                f"- Decision: `{best.get('payment_decision', '')}`",
                f"- URL: `{best.get('normalized_url', '')}`",
                "",
                "### Positive evidence",
                "",
                str(best.get("positive_evidence", "")),
                "",
                "### Risks",
                "",
                str(best.get("risk_evidence", "")) or "Nenhum risco textual relevante detectado.",
            ]
        )
    else:
        lines.extend(
            [
                "",
                "## Decision",
                "",
                "**Nenhuma oportunidade atingiu confiança suficiente para execução.**",
                "",
                "O Brain permanecerá em modo de descoberta e refinamento.",
            ]
        )

    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_best_target(approved: list[dict[str, Any]]) -> None:
    OUTPUT_TARGET.parent.mkdir(parents=True, exist_ok=True)

    if not approved:
        OUTPUT_TARGET.write_text(
            "# Current Best Target\n\n"
            "Status: `NO_PAYMENT_VERIFIED_CANDIDATE`\n\n"
            "Nenhuma oportunidade atingiu o limiar mínimo de confiança.\n",
            encoding="utf-8",
        )
        return

    best = approved[0]

    content = f"""# Current Best Target

Status: `{best['payment_decision']}`

- Repository: `{best.get('normalized_repository', '')}`
- Issue: `{best.get('normalized_issue_number', '')}`
- Title: {best.get('normalized_title', '')}
- Reward USD: `{best.get('reward_usd', 0)}`
- Estimated hours: `{best.get('estimated_hours', 0)}`
- Revenue per hour: `{best.get('estimated_revenue_per_hour', 0)}`
- Payment confidence: `{best.get('payment_confidence_score', 0)}`
- Source: `{best.get('normalized_source_name', '')}`
- URL: `{best.get('normalized_url', '')}`

## Evidence

{best.get('positive_evidence', '')}

## Risks

{best.get('risk_evidence', '') or 'Nenhum risco textual relevante detectado.'}
"""
    OUTPUT_TARGET.write_text(content, encoding="utf-8")


def write_execution_handoff(approved: list[dict[str, Any]]) -> None:
    OUTPUT_HANDOFF.parent.mkdir(parents=True, exist_ok=True)

    auto = [
        record
        for record in approved
        if record["payment_decision"] == "AUTO_START_LOCAL_EXECUTION"
    ]

    if not auto:
        if OUTPUT_HANDOFF.exists():
            OUTPUT_HANDOFF.unlink()
        return

    best = auto[0]

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "READY_FOR_LOCAL_EXECUTION_START",
        "repository": best.get("normalized_repository", ""),
        "issue_number": best.get("normalized_issue_number", ""),
        "title": best.get("normalized_title", ""),
        "url": best.get("normalized_url", ""),
        "reward_usd": best.get("reward_usd", 0),
        "estimated_hours": best.get("estimated_hours", 0),
        "payment_confidence_score": best.get("payment_confidence_score", 0),
        "positive_evidence": best.get("positive_evidence", ""),
        "risk_evidence": best.get("risk_evidence", ""),
        "source_file": best.get("_source_file", ""),
    }

    OUTPUT_HANDOFF.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    raw_candidates = load_candidates()

    scored = [
        score_candidate(row, source_file)
        for row, source_file in raw_candidates
    ]

    ranked = deduplicate(scored)
    ranked.sort(
        key=lambda record: (
            float(record["payment_confidence_score"]),
            float(record["estimated_revenue_per_hour"]),
            float(record["reward_usd"]),
        ),
        reverse=True,
    )

    approved = [
        record
        for record in ranked
        if record["payment_decision"]
        in {"PAYMENT_VERIFIED_CANDIDATE", "AUTO_START_LOCAL_EXECUTION"}
    ]

    rejected = [
        record
        for record in ranked
        if record["payment_decision"] == "REJECTED"
    ]

    write_csv(OUTPUT_RANKING, ranked)
    write_csv(OUTPUT_APPROVED, approved)
    write_csv(OUTPUT_REJECTED, rejected)
    write_report(ranked, approved, rejected)
    write_best_target(approved)
    write_execution_handoff(approved)

    print("===== PAYMENT CONFIDENCE ENGINE =====")
    print(f"Raw candidates: {len(raw_candidates)}")
    print(f"Unique candidates: {len(ranked)}")
    print(f"Payment-verified: {len(approved)}")
    print(
        "Auto-start local execution: "
        + str(
            sum(
                1
                for record in approved
                if record["payment_decision"]
                == "AUTO_START_LOCAL_EXECUTION"
            )
        )
    )
    print(f"Rejected: {len(rejected)}")

    if approved:
        best = approved[0]
        print("")
        print("BEST TARGET")
        print(f"Repository: {best.get('normalized_repository', '')}")
        print(f"Issue: {best.get('normalized_issue_number', '')}")
        print(f"Reward: USD {best.get('reward_usd', 0):.2f}")
        print(
            "Confidence: "
            f"{best.get('payment_confidence_score', 0):.2f}"
        )
        print(f"Decision: {best.get('payment_decision', '')}")
    else:
        print("")
        print("NO_PAYMENT_VERIFIED_CANDIDATE")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())





