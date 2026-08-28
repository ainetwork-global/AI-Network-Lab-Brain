from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PLATFORMS = ROOT / "04_OPPORTUNITIES" / "participant_platform_status.csv"
DECISIONS = ROOT / "04_OPPORTUNITIES" / "GLOBAL_DECISION_QUEUE.csv"
OUTPUT = ROOT / "04_OPPORTUNITIES" / "HUMAN_LOGIN_HANDOFF_QUEUE.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_HUMAN_LOGIN_HANDOFFS.md"


def read(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def handoff_id(kind: str, url: str) -> str:
    return hashlib.sha256(f"{kind}:{url}".encode()).hexdigest()[:16]


def main() -> int:
    generated = datetime.now(timezone.utc).isoformat()
    rows: list[dict[str, str]] = []

    for platform in read(PLATFORMS):
        public = platform.get("monitor_mode") == "public_jobs"
        status = "PUBLIC_SCAN_AVAILABLE" if public else "LOGIN_REQUIRED_TO_DISCOVER"
        human_step = (
            "Nenhum login necessário para consultar vagas públicas."
            if public else
            "Abra a plataforma, faça login na sua própria conta e avise: login concluído."
        )
        resume = (
            "Validar vagas públicas, requisitos e elegibilidade."
            if public else
            "Inspecionar as oportunidades exibidas na conta, classificar retorno e preparar a execução permitida."
        )
        rows.append({
            "handoff_id": handoff_id("platform", platform.get("url", "")),
            "handoff_type": "authenticated_platform",
            "platform": platform.get("name", ""),
            "opportunity_title": "Oportunidades personalizadas da conta",
            "url": platform.get("url", ""),
            "category": platform.get("category", ""),
            "payment_method": platform.get("payment", ""),
            "country_eligibility": platform.get("brazil", ""),
            "handoff_status": status,
            "human_step": human_step,
            "assistant_resume_action": resume,
            "identity_action_owner": "account_holder",
            "answers_and_recordings_owner": "account_holder",
            "initial_cost_allowed": "false",
            "external_submission_allowed": "false",
            "detected_at": platform.get("checked_at", generated),
        })

    for candidate in read(DECISIONS):
        if candidate.get("decision_route") != "HUMAN_DECISION_REQUIRED":
            continue
        rows.append({
            "handoff_id": handoff_id("candidate", candidate.get("url", "")),
            "handoff_type": "candidate_decision",
            "platform": candidate.get("source", ""),
            "opportunity_title": candidate.get("title", ""),
            "url": candidate.get("url", ""),
            "category": candidate.get("category", ""),
            "payment_method": candidate.get("payment_method", ""),
            "country_eligibility": candidate.get("country_eligibility", ""),
            "handoff_status": "HUMAN_REVIEW_REQUIRED",
            "human_step": candidate.get("decision_next_action", "Revisar e autorizar a preparação."),
            "assistant_resume_action": "Continuar validação e preparação interna após a decisão humana.",
            "identity_action_owner": "account_holder",
            "answers_and_recordings_owner": "account_holder",
            "initial_cost_allowed": "false",
            "external_submission_allowed": "false",
            "detected_at": candidate.get("decision_generated_at", generated),
        })

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0]) if rows else ["handoff_id", "handoff_status"]
    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    login = sum(row["handoff_status"] == "LOGIN_REQUIRED_TO_DISCOVER" for row in rows)
    review = sum(row["handoff_status"] == "HUMAN_REVIEW_REQUIRED" for row in rows)
    public = sum(row["handoff_status"] == "PUBLIC_SCAN_AVAILABLE" for row in rows)
    lines = [
        "# HUMAN LOGIN HANDOFF QUEUE", "",
        f"Generated: `{generated}`", "",
        f"- Login required to discover personalized opportunities: **{login}**",
        f"- Candidate decisions awaiting human review: **{review}**",
        f"- Public scans available: **{public}**", "",
        "The account holder performs login, identity verification, truthful answers, interviews and recordings.",
        "The Brain resumes inspection, ranking, preparation and other reversible work after the user confirms login.",
        "No application, claim, submission, signature, purchase or payment was performed.", "",
        "| Platform | Status | Human step | Brain resumes with |", "|---|---|---|---|",
    ]
    for row in rows:
        lines.append(f"| {row['platform']} | {row['handoff_status']} | {row['human_step']} | {row['assistant_resume_action']} |")
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"login_required={login}; human_review={review}; public_scan={public}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
