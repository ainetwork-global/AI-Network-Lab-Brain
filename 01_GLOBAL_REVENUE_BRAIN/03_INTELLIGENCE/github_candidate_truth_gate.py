from __future__ import annotations

import csv
import json
import os
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "04_OPPORTUNITIES" / "VERIFIED_EXECUTION_QUEUE.csv"
ALGORA_INPUT = ROOT / "04_OPPORTUNITIES" / "algora_open_bounties.csv"
OFFICIAL_SOURCE_INPUT = ROOT / "04_OPPORTUNITIES" / "official_source_candidates.csv"
OFFICIAL_ELIGIBILITY_INPUT = ROOT / "04_OPPORTUNITIES" / "official_eligible_queue.csv"
OUTPUT = ROOT / "04_OPPORTUNITIES" / "LIVE_TRUTH_EXECUTION_QUEUE.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_LIVE_TRUTH_QUEUE.md"
TARGET = ROOT / "00_CURRENT_STATE" / "CURRENT_BEST_TARGET.md"
TODAY = datetime.now(timezone.utc).date()

REWARD_OFFER = re.compile(r"(?i)(?:\b(?:bounty|reward|prize|payout)\b[^\n]{0,80}(?:[$€£]|usd|usdc|eur|gbp|\d)|(?:[$€£]|usd|usdc|eur|gbp)\s*\d[^\n]{0,80}\b(?:bounty|reward|prize|payout)\b|usd for an accepted submission|payment (?:is|will be) [^\n]{0,80}(?:[$€£]|usd|usdc|eur|gbp))")
COST = re.compile(r"(?i)\b(claim bond|entry fee|application fee|deposit required|stake required|purchase required|subscription required|buy (?:a |the )?token|pay to (?:claim|join|apply))\b")
DEADLINE = re.compile(r"(?i)\bdeadline\b[^\n]{0,80}?\b(20\d{2})[-/](\d{1,2})[-/](\d{1,2})\b")
GITHUB_ISSUE = re.compile(r"https?://github\.com/([^/]+)/([^/]+)/(?:issues|pull)/(\d+)")

UNFUNDED = re.compile(r"(?is)\bUNFUNDED\b|cashier status:\s*BLOCKED|no .?FUNDED.? comment|deliver(?:y)? only after funding|awaiting funding")
FUNDING_EVIDENCE = re.compile(r"(?is)\bFUNDED\b[^\n]{0,240}(?:basescan\.org/(?:tx|address)/0x[a-f0-9]+|tx(?:id| hash)?\s*[:=]\s*0x[a-f0-9]{16,})")
SELF_REVENUE_GOAL = re.compile(r"(?is)\b(first verified revenue|objective.{0,80}(?:obtain|earn|generate) revenue|revenue definition|revenue target|goal.{0,80}(?:usd|usdc|revenue))\b")

ACTIVE_WORK = re.compile(r"(?is)(?:draft pull request|opened (?:a )?pull request|github\.com/[^\s]+/pull/\d+)")

FIELDS = [
    "truth_rank", "truth_status", "truth_reason", "live_state", "comments",
    "open_competing_prs", "reward_basis", "source_validation",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def positive_number(value: object) -> float | None:
    try:
        number = float(str(value or "").replace(",", ""))
    except ValueError:
        return None
    return number if number > 0 else None


def canonical_official_candidates() -> dict[str, dict[str, str]]:
    """Return authoritative program metadata keyed by canonical URL.

    Discovery/verification pages can expose both a maximum bounty and a vault
    balance.  The official adapter already stores the labelled maximum bounty,
    so it must win over an amount later scraped without context.
    """
    eligibility_by_url = {
        row.get("url", ""): row
        for row in read_csv(OFFICIAL_ELIGIBILITY_INPUT)
        if row.get("url")
    }
    result: dict[str, dict[str, str]] = {}
    for row in read_csv(OFFICIAL_SOURCE_INPUT):
        url = row.get("url", "")
        if not url:
            continue
        merged = dict(row)
        eligible = eligibility_by_url.get(url, {})
        for key in ("kyc_required", "eligibility_status", "eligibility_notes"):
            if eligible.get(key, "") != "":
                merged[key] = eligible[key]
        result[url] = merged
    return result


def apply_official_truth(
    row: dict[str, str], official: dict[str, dict[str, str]]
) -> dict[str, str]:
    result = dict(row)
    canonical = official.get(row.get("url", ""))
    if not canonical:
        result.setdefault("reward_basis", "reported_amount_unverified")
        result.setdefault("source_validation", "unverified")
        return result
    canonical_reward = positive_number(canonical.get("reward_amount"))
    if canonical_reward is not None:
        result["reward_amount"] = str(canonical_reward)
        result["reward_currency"] = canonical.get("reward_currency") or "USD"
        result["reward_basis"] = "maximum_advertised_reward"
    for key in ("kyc_required", "eligibility_status", "eligibility_notes"):
        if canonical.get(key, "") != "":
            result[key] = canonical[key]
    result["source_validation"] = "official_adapter"
    return result

def api(path: str) -> dict:
    request = urllib.request.Request(
        f"https://api.github.com{path}",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {os.environ.get('GITHUB_TOKEN', '')}",
            "X-GitHub-Api-Version": "2022-11-28",
            "User-Agent": "global-revenue-brain",
        },
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.load(response)

def competing_pull_requests(owner: str, repo: str, number: str, issue_title: str) -> list[int]:
    """Return open PRs that explicitly reference or closely match this issue."""
    try:
        pulls = api(f"/repos/{owner}/{repo}/pulls?state=open&per_page=100")
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
    ):
        return []

    normalized_issue = re.sub(r"(?i)\\b(?:bounty|reward)\\b|[^a-z0-9]+", " ", issue_title.lower()).strip()
    matches: list[int] = []
    for pull in pulls if isinstance(pulls, list) else []:
        if not isinstance(pull, dict):
            continue
        title = str(pull.get("title") or "")
        body = str(pull.get("body") or "")
        haystack = f"{title}\\n{body}"
        explicit_reference = bool(
            re.search(rf"(?i)(?:fix(?:e[sd])?|close[sd]?|resolve[sd]?)?\\s*#{re.escape(number)}\\b", haystack)
            or f"/issues/{number}" in haystack
        )
        normalized_pr = re.sub(r"(?i)\\b(?:feat|fix|implement|implementation)\\b|[^a-z0-9]+", " ", title.lower()).strip()
        close_title = bool(
            normalized_issue
            and normalized_pr
            and SequenceMatcher(None, normalized_issue, normalized_pr).ratio() >= 0.62
        )
        if explicit_reference or close_title:
            matches.append(int(pull.get("number") or 0))
    return [pull_number for pull_number in matches if pull_number]


def classify(row: dict[str, str]) -> tuple[str, str, str, int]:
    match = GITHUB_ISSUE.match(row.get("url", ""))
    if not match:
        source = row.get("source", "").lower()
        category = row.get("category", "").lower()
        if "immunefi" in source and category == "authorized_bug_bounty":
            requirements = ["escopo", "PoC", "ativos e impactos elegíveis"]
            if str(row.get("kyc_required", "")).lower() in {"1", "true", "yes"}:
                requirements.append("KYC")
            return (
                "AUTHORIZED_BUG_BOUNTY_REVIEW_REQUIRED",
                "Programa oficial identificado; revisar "
                + ", ".join(requirements)
                + " antes de qualquer teste exclusivamente local.",
                "official_program",
                0,
            )
        return (
            "SOURCE_REVIEW_REQUIRED",
            "Fonte externa ainda exige validação específica da plataforma.",
            "external_source",
            0,
        )
    owner, repo, number = match.groups()
    try:
        issue = api(f"/repos/{owner}/{repo}/issues/{number}")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError) as error:
        return "LIVE_CHECK_RETRY_REQUIRED", f"Falha temporária na validação ao vivo: {type(error).__name__}.", "unknown", 0

    state = str(issue.get("state", "unknown")).lower()
    comments = int(issue.get("comments", 0) or 0)
    try:
        comment_rows = api(
            f"/repos/{owner}/{repo}/issues/{number}/comments?per_page=100"
        )
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        json.JSONDecodeError,
    ):
        comment_rows = []
    comment_text = "\n".join(
        str(item.get("body", ""))
        for item in comment_rows
        if isinstance(item, dict)
    )
    issue_body = str(issue.get("body") or "")
    text = (
        f"{issue.get('title', '')}\n"
        f"{issue_body}\n"
        f"{comment_text}"
    )
    if re.search(r"(?i)\\bfor an accepted submission\\b", issue_body):
        row["reward_basis"] = "accepted_submission_not_guaranteed"
    if re.search(r"(?i)payment details will be handled privately after acceptance", issue_body):
        row["payment_method"] = "private_after_acceptance"
        row["kyc_required"] = "unknown_not_disclosed"

    updated_at_raw = str(issue.get("updated_at") or "")
    try:
        updated_at = datetime.fromisoformat(updated_at_raw.replace("Z", "+00:00"))
    except ValueError:
        updated_at = datetime.now(timezone.utc)
    if issue.get("locked") and updated_at < datetime.now(timezone.utc) - timedelta(days=180):
        return "STALE_LOCKED_CONFIRMATION_REQUIRED", "Issue bloqueada para comentários e sem atualização há mais de 180 dias; confirmar se a recompensa continua executável.", state, comments

    if state != "open":
        return "BLOCKED_CLOSED_OR_COMPLETED", "A API do GitHub informa que a oportunidade não está aberta.", state, comments
    labels = {
        str(label.get("name") or "").lower()
        for label in issue.get("labels", [])
        if isinstance(label, dict)
    }
    if "external-mirror" in labels or re.search(r"(?i)external\s+bounty\s+mirror|bounty\s+task\s+mirror|原\s*issue", text):
        return "BLOCKED_EXTERNAL_MIRROR", "É um espelho/agregador; somente a issue original pode ser validada e executada.", state, comments
    if SELF_REVENUE_GOAL.search(text):
        return "BLOCKED_NOT_A_PAID_TASK", "A issue descreve uma meta interna de receita, não uma oferta de trabalho paga.", state, comments
    if UNFUNDED.search(text) and not FUNDING_EVIDENCE.search(text):
        return "BLOCKED_UNFUNDED", "O próprio protocolo informa que a recompensa ainda não foi financiada.", state, comments
    if COST.search(text):
        return "BLOCKED_INITIAL_COST", "Exige depósito, taxa, bond, stake, compra ou assinatura.", state, comments
    if not REWARD_OFFER.search(text):
        return "BLOCKED_REWARD_CONTEXT_FALSE_POSITIVE", "O valor encontrado não aparece em contexto explícito de prêmio/pagamento.", state, comments
    deadline = DEADLINE.search(text)
    if deadline:
        try:
            date = datetime(int(deadline[1]), int(deadline[2]), int(deadline[3])).date()
            if date < TODAY:
                return "BLOCKED_DEADLINE_EXPIRED", f"Prazo explícito expirou em {date.isoformat()}.", state, comments
        except ValueError:
            pass
    lowered = text.lower()
    if "winner announcement" in lowered and re.search(r"\b20(?:1\d|2[0-5])\b", lowered):
        return "BLOCKED_STALE_COMPETITION", "Competição antiga com anúncio de vencedor já previsto.", state, comments
    competing_prs = competing_pull_requests(owner, repo, number, str(issue.get("title") or ""))
    row["_open_competing_prs"] = str(len(competing_prs))
    if len(competing_prs) >= 3:
        listed = ", ".join(f"#{item}" for item in competing_prs[:5])
        return "BLOCKED_HIGH_COMPETITION", f"Há {len(competing_prs)} PRs concorrentes relacionados (incluindo {listed}); não investir trabalho nesta oportunidade saturada.", state, comments
    if competing_prs:
        listed = ", ".join(f"#{item}" for item in competing_prs[:5])
        return "ACTIVE_WORK_CONFIRMATION_REQUIRED", f"Há {len(competing_prs)} PR(s) concorrente(s) relacionado(s) ({listed}); confirmar disponibilidade antes de desenvolver.", state, comments
    if re.search(r"(?i)\b(8|eight|10|ten)\s+(?:distinct\s+)?(?:ai\s+)?(?:systems|models|model families)\b", text):
        return "RESOURCE_AND_COMPETITION_REVIEW_REQUIRED", f"Demanda múltiplos modelos/serviços; há {comments} comentários concorrentes.", state, comments
    if ACTIVE_WORK.search(comment_text) or issue.get("assignee"):
        return "ACTIVE_WORK_CONFIRMATION_REQUIRED", "Há PR/trabalho ativo ou responsável atribuído; confirmar disponibilidade antes de desenvolver.", state, comments
    if comments >= 25:
        return "BLOCKED_HIGH_COMPETITION", f"Há {comments} comentários concorrentes; oportunidade saturada e inadequada para investimento automático.", state, comments
    if comments >= 8:
        return "COMPETITION_REVIEW_REQUIRED", f"Há {comments} comentários; concorrência deve ser avaliada antes de investir trabalho.", state, comments
    if not row.get("payment_method", "").strip():
        return "PAYMENT_EVIDENCE_REVIEW_REQUIRED", "Rota e evidência de pagamento ainda não foram confirmadas.", state, comments
    return "READY_FOR_TECHNICAL_REVIEW", "Aberta, prêmio contextual, sem custo inicial detectado e com rota de pagamento informada.", state, comments

def main() -> int:
    rows = read_csv(INPUT)
    official = canonical_official_candidates()
    candidates = [
        r for r in rows
        if r.get("queue_status", "").endswith("REVIEW_REQUIRED")
        or r.get("queue_status") == "READY_FOR_TECHNICAL_REVIEW"
    ]
    known_urls = {r.get("url", "") for r in candidates}
    if ALGORA_INPUT.exists():
        with ALGORA_INPUT.open(
            encoding="utf-8-sig",
            newline="",
        ) as handle:
            for bounty in csv.DictReader(handle):
                url = str(bounty.get("github_url") or "").strip()
                if not url or url in known_urls:
                    continue
                candidates.append(
                    {
                        "rank": bounty.get("id", ""),
                        "queue_status": "ALGORA_STAGED",
                        "verification_score": bounty.get("candidate_score", ""),
                        "priority_score": bounty.get("candidate_score", ""),
                        "title": bounty.get("title", ""),
                        "category": "coding_bounty",
                        "source": "Algora Open Bounties",
                        "url": url,
                        "reward_amount": bounty.get("reward_amount", ""),
                        "reward_currency": bounty.get("reward_currency", "USD"),
                        "payment_method": "Algora",
                        "difficulty": "",
                        "estimated_hours": "",
                        "risk_level": "baixo",
                        "country_eligibility": "UNKNOWN_REVIEW_REQUIRED",
                        "country_restrictions": "",
                        "kyc_required": "1",
                        "human_approval_required": "1",
                        "verification_status": "algora_comment_validation",
                        "recommended_action": "Review live bounty comments",
                        "recommendation_reason": "Official Algora evidence is stored in GitHub comments.",
                        "verified_at": "",
                    }
                )
                known_urls.add(url)
    candidates = candidates[:60]
    output = []
    for row in candidates:
        row = apply_official_truth(row, official)
        status, reason, state, comments = classify(row)
        result = dict(row)
        if status == "BLOCKED_HIGH_COMPETITION":
            row["recommended_action"] = "Não iniciar. Arquivar e priorizar oportunidade com concorrência baixa."
        elif status == "ACTIVE_WORK_CONFIRMATION_REQUIRED":
            row["recommended_action"] = "Confirmar com o mantenedor se novas submissões ainda são aceitas antes de qualquer trabalho."
        result.update({"truth_status": status, "truth_reason": reason, "live_state": state, "comments": comments, "open_competing_prs": row.pop("_open_competing_prs", "")})
        output.append(result)
    order = {"READY_FOR_TECHNICAL_REVIEW": 0, "PAYMENT_EVIDENCE_REVIEW_REQUIRED": 1, "COMPETITION_REVIEW_REQUIRED": 2, "RESOURCE_AND_COMPETITION_REVIEW_REQUIRED": 3}
    output.sort(key=lambda r: (order.get(r["truth_status"], 9), -float(r.get("priority_score") or 0)))
    for rank, row in enumerate(output, 1):
        row["truth_rank"] = rank
    fieldnames = FIELDS + [f for f in rows[0].keys() if f not in FIELDS] if rows else FIELDS
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(output)
    ready = [r for r in output if r["truth_status"] == "READY_FOR_TECHNICAL_REVIEW"]
    review = [r for r in output if r["truth_status"].endswith("REVIEW_REQUIRED")]
    lines = ["# LIVE TRUTH EXECUTION QUEUE", "", f"Generated at: `{datetime.now(timezone.utc).isoformat()}`", "", f"- Live candidates checked: **{len(output)}**", f"- Ready for technical review: **{len(ready)}**", f"- Human/resource review required: **{len(review)}**", f"- Blocked: **{len(output)-len(ready)-len(review)}**", "", "No claim, submission, contract, wallet signature, purchase, deposit, or financial transaction was performed.", ""]
    for row in output[:25]:
        lines += [f"## {row['truth_rank']}. {row.get('title','')}", "", f"- Truth status: `{row['truth_status']}`", f"- Reason: {row['truth_reason']}", f"- Live GitHub state: `{row['live_state']}`", f"- Comments: `{row['comments']}`", f"- Reward: `{row.get('reward_currency','')} {row.get('reward_amount','')}`", f"- URL: {row.get('url','')}", ""]
    REPORT.write_text("\n".join(lines), encoding="utf-8")
    best = ready[0] if ready else (review[0] if review else None)
    if best:
        content = f"# Current Best Target\n\nStatus: `{best['truth_status']}`\n\nTitle: {best.get('title','')}\nReward: {best.get('reward_currency','')} {best.get('reward_amount','')}\nURL: {best.get('url','')}\n\nReason: {best['truth_reason']}\n\nExternal action performed: `false`\n"
    else:
        content = "# Current Best Target\n\nStatus: `NO_PAYMENT_VERIFIED_CANDIDATE`\n\nNenhuma oportunidade passou pela validação contextual e ao vivo.\n"
    TARGET.write_text(content, encoding="utf-8")
    print(f"Live checked: {len(output)}; ready: {len(ready)}; review: {len(review)}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
