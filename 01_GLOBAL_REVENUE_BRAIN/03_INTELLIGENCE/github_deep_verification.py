from __future__ import annotations

import csv
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT = ROOT / "12_REPORTS" / "LATEST_GITHUB_DEEP_VERIFICATION.md"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "github_deep_verified_queue.csv"

HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "Global-Revenue-Brain/1.0",
    "X-GitHub-Api-Version": "2022-11-28",
}

REWARD_TERMS = (
    "bounty",
    "reward",
    "prize",
    "payout",
    "compensation",
    "paid upon",
    "will receive",
    "winner receives",
)

NEGATIVE_TERMS = {
    "unfunded": "recompensa explicitamente não financiada",
    "volunteer": "trabalho voluntário",
    "no cash": "sem pagamento em dinheiro",
    "free": "atividade declarada como gratuita",
    "test bounty": "bounty de teste",
    "canary": "teste canário",
    "example": "conteúdo de exemplo",
    "demo": "demonstração",
}

AGGREGATOR_TERMS = (
    "bounty alert",
    "new opportunities",
    "awesome-agent-bounties",
    "opportunity list",
    "curated list",
    "weekly roundup",
)

APPLICATION_TERMS = (
    "grant application",
    "funding proposal",
    "application -",
    "proposal:",
)

CLAIM_TERMS = (
    "comment to claim",
    "claim this issue",
    "apply by commenting",
    "submit a pull request",
    "send your proposal",
)

PAYMENT_PATTERNS = [
    re.compile(
        r"(?:bounty|reward|prize|payout|compensation|budget)"
        r"[^.\n]{0,100}"
        r"(?:US\$|USD|\$|USDC|USDT|EUR|€|GBP|£)\s*"
        r"\d[\d,.]*",
        re.I,
    ),
    re.compile(
        r"(?:US\$|USD|\$|USDC|USDT|EUR|€|GBP|£)\s*"
        r"\d[\d,.]*"
        r"[^.\n]{0,100}"
        r"(?:bounty|reward|prize|payout|compensation)",
        re.I,
    ),
]


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
        "deep_verification_status": "TEXT",
        "deep_verification_score": "REAL",
        "deep_verification_reason": "TEXT",
        "github_issue_state": "TEXT",
        "github_repo_archived": "INTEGER",
        "github_repo_disabled": "INTEGER",
        "github_is_pull_request": "INTEGER",
        "github_author_association": "TEXT",
        "github_labels": "TEXT",
        "github_updated_at": "TEXT",
        "deep_verified_at": "TEXT",
    }

    for name, data_type in additions.items():
        if name not in columns:
            conn.execute(
                f"ALTER TABLE opportunity_verifications "
                f"ADD COLUMN {name} {data_type}"
            )

    conn.commit()


def parse_github_issue_url(url: str):
    match = re.match(
        r"^https://github\.com/([^/]+)/([^/]+)/issues/(\d+)(?:/.*)?$",
        url.strip(),
        re.I,
    )

    if not match:
        return None

    return match.group(1), match.group(2), int(match.group(3))


def fetch_json(url: str):
    response = requests.get(url, headers=HEADERS, timeout=25)

    remaining = response.headers.get("X-RateLimit-Remaining")
    if remaining is not None:
        print(f"GitHub API restante: {remaining}")

    if response.status_code == 404:
        return None, "não encontrado"

    if response.status_code == 403:
        return None, "limite ou acesso negado pela API do GitHub"

    response.raise_for_status()
    return response.json(), None


def classify(issue, repo, title, stored_reward):
    body = issue.get("body") or ""
    live_title = issue.get("title") or title or ""
    combined = f"{live_title}\n{body}".lower()

    reasons = []
    score = 50.0

    state = issue.get("state", "")
    archived = bool(repo.get("archived"))
    disabled = bool(repo.get("disabled"))
    is_pr = "pull_request" in issue

    if state != "open":
        score -= 60
        reasons.append("issue fechada")

    if archived:
        score -= 60
        reasons.append("repositório arquivado")

    if disabled:
        score -= 60
        reasons.append("repositório desativado")

    if is_pr:
        score -= 50
        reasons.append("URL representa pull request, não oportunidade")

    for term, reason in NEGATIVE_TERMS.items():
        if term in combined:
            score -= 45
            reasons.append(reason)

    if any(term in combined for term in AGGREGATOR_TERMS):
        score -= 55
        reasons.append("registro aparenta ser agregador ou alerta, não bounty direto")

    if any(term in combined for term in APPLICATION_TERMS):
        score -= 45
        reasons.append(
            "registro aparenta ser candidatura/proposta já criada, não programa aberto"
        )

    payment_evidence = any(
        pattern.search(f"{live_title}\n{body}")
        for pattern in PAYMENT_PATTERNS
    )

    reward_context = any(term in combined for term in REWARD_TERMS)

    if payment_evidence:
        score += 25
        reasons.append("pagamento contextual encontrado no conteúdo oficial")
    elif stored_reward:
        score -= 25
        reasons.append(
            "valor armazenado não foi confirmado com contexto no conteúdo oficial"
        )
    else:
        score -= 15
        reasons.append("recompensa monetária não confirmada")

    if reward_context:
        score += 10

    if any(term in combined for term in CLAIM_TERMS):
        score += 12
        reasons.append("mecanismo de candidatura ou claim identificado")
    else:
        reasons.append("mecanismo de candidatura não identificado")

    labels = [
        str(label.get("name", "")).lower()
        for label in issue.get("labels", [])
        if isinstance(label, dict)
    ]

    if any(
        value in " ".join(labels)
        for value in ("bounty", "reward", "paid", "help wanted")
    ):
        score += 8
        reasons.append("label compatível com oportunidade")

    score = round(max(0, min(100, score)), 2)

    if score >= 75:
        status = "deep_actionable"
    elif score >= 55:
        status = "manual_review"
    else:
        status = "deep_rejected"

    return status, score, "; ".join(dict.fromkeys(reasons))


conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row
ensure_columns(conn)

rows = conn.execute(
    """
    SELECT *
    FROM opportunity_verifications
    WHERE origin = 'external'
      AND verification_status IN (
          'actionable',
          'approval_required',
          'verified'
      )
      AND url LIKE 'https://github.com/%/issues/%'
    ORDER BY verification_score DESC
    LIMIT 30
    """
).fetchall()

results = []

print()
print("===== GITHUB DEEP VERIFICATION =====")
print(f"Selecionadas: {len(rows)}")

for index, row in enumerate(rows, 1):
    parsed = parse_github_issue_url(row["url"])

    if not parsed:
        continue

    owner, repository, issue_number = parsed

    print()
    print(f"[{index}/{len(rows)}] {owner}/{repository}#{issue_number}")
    print(row["title"])

    issue, issue_error = fetch_json(
        f"https://api.github.com/repos/{owner}/{repository}/issues/{issue_number}"
    )
    repo, repo_error = fetch_json(
        f"https://api.github.com/repos/{owner}/{repository}"
    )

    if issue_error or repo_error or not issue or not repo:
        status = "manual_review"
        score = 25.0
        reason = issue_error or repo_error or "falha de consulta"

        metadata = {
            "state": None,
            "archived": None,
            "disabled": None,
            "is_pr": None,
            "author_association": None,
            "labels": [],
            "updated_at": None,
        }
    else:
        status, score, reason = classify(
            issue,
            repo,
            row["title"],
            row["reward_amount"],
        )

        metadata = {
            "state": issue.get("state"),
            "archived": int(bool(repo.get("archived"))),
            "disabled": int(bool(repo.get("disabled"))),
            "is_pr": int("pull_request" in issue),
            "author_association": issue.get("author_association"),
            "labels": [
                label.get("name")
                for label in issue.get("labels", [])
                if isinstance(label, dict)
            ],
            "updated_at": issue.get("updated_at"),
        }

    conn.execute(
        """
        UPDATE opportunity_verifications
        SET
            deep_verification_status = ?,
            deep_verification_score = ?,
            deep_verification_reason = ?,
            github_issue_state = ?,
            github_repo_archived = ?,
            github_repo_disabled = ?,
            github_is_pull_request = ?,
            github_author_association = ?,
            github_labels = ?,
            github_updated_at = ?,
            deep_verified_at = ?
        WHERE id = ?
        """,
        (
            status,
            score,
            reason,
            metadata["state"],
            metadata["archived"],
            metadata["disabled"],
            metadata["is_pr"],
            metadata["author_association"],
            json.dumps(metadata["labels"], ensure_ascii=False),
            metadata["updated_at"],
            utc_now(),
            row["id"],
        ),
    )

    results.append({
        "id": row["id"],
        "title": row["title"],
        "url": row["url"],
        "reward_amount": row["reward_amount"],
        "reward_currency": row["reward_currency"],
        "status": status,
        "score": score,
        "reason": reason,
        "issue_state": metadata["state"],
        "repository_archived": metadata["archived"],
        "labels": ", ".join(metadata["labels"]),
    })

    print(f"status: {status}")
    print(f"score: {score}")
    print(f"motivo: {reason}")

conn.commit()

results.sort(
    key=lambda item: (
        item["status"] != "deep_actionable",
        -item["score"],
    )
)

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

fields = [
    "id",
    "title",
    "url",
    "reward_amount",
    "reward_currency",
    "status",
    "score",
    "reason",
    "issue_state",
    "repository_archived",
    "labels",
]

with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

counts = {}

for result in results:
    counts[result["status"]] = counts.get(result["status"], 0) + 1

lines = [
    "# Global Revenue Brain — Verificação Profunda GitHub",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Resumo",
    "",
    f"- Total analisado: **{len(results)}**",
    f"- Deep actionable: **{counts.get('deep_actionable', 0)}**",
    f"- Revisão manual: **{counts.get('manual_review', 0)}**",
    f"- Rejeitadas: **{counts.get('deep_rejected', 0)}**",
    "",
    "## Ranking",
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
        f"- Status: **{result['status']}**",
        f"- Score profundo: **{result['score']}**",
        f"- Recompensa anterior: {reward}",
        f"- Estado GitHub: {result['issue_state']}",
        f"- Labels: {result['labels'] or 'nenhuma'}",
        f"- Motivo: {result['reason']}",
        f"- URL: {result['url']}",
        "",
    ])

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== DEEP VERIFICATION SUMMARY =====")
print(f"Analisadas: {len(results)}")
print(f"Deep actionable: {counts.get('deep_actionable', 0)}")
print(f"Manual review: {counts.get('manual_review', 0)}")
print(f"Deep rejected: {counts.get('deep_rejected', 0)}")

print()
print("===== DEEP ACTIONABLE =====")

actionable = [
    result for result in results
    if result["status"] == "deep_actionable"
]

for index, result in enumerate(actionable, 1):
    print()
    print(f"{index}. {result['title']}")
    print(f"   score: {result['score']}")
    print(f"   recompensa: {result['reward_currency']} {result['reward_amount']}")
    print(f"   motivo: {result['reason']}")
    print(f"   url: {result['url']}")

conn.close()
