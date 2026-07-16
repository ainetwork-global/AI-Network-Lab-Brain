from __future__ import annotations

import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATABASE = ROOT / "11_DATA" / "global_revenue_brain.db"
CSV_PATH = ROOT / "04_OPPORTUNITIES" / "gemini_xprize_project_candidates.csv"
REPORT = ROOT / "12_REPORTS" / "LATEST_GEMINI_XPRIZE_PROJECT_SELECTION.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


CANDIDATES = [
    {
        "project_key": "revenue_rescue",
        "name": "Revenue Rescue AI",
        "category": "Small Business Services",
        "problem": (
            "Pequenos negócios perdem vendas porque não conseguem "
            "responder leads, criar propostas e acompanhar cobranças."
        ),
        "solution": (
            "Agente Gemini que recebe um lead, qualifica a oportunidade, "
            "gera proposta comercial, cria plano de acompanhamento e "
            "mantém um painel de receita recuperável."
        ),
        "google_cloud": (
            "Cloud Run, Firestore, Cloud Storage e Gemini API."
        ),
        "monetization": (
            "Assinatura mensal e cobrança por proposta processada."
        ),
        "build_days": 14,
        "technical_fit": 0.94,
        "launch_speed": 0.94,
        "revenue_speed": 0.90,
        "demo_strength": 0.92,
        "novelty": 0.78,
        "operational_risk": 0.22,
        "dependency_risk": 0.18,
    },
    {
        "project_key": "cashflow_guard",
        "name": "CashFlow Guard AI",
        "category": "Money & Financial Access",
        "problem": (
            "Microempresas não conseguem prever falta de caixa nem "
            "priorizar cobranças e despesas."
        ),
        "solution": (
            "Copiloto financeiro Gemini que classifica entradas e saídas, "
            "prevê risco de caixa e sugere ações autorizadas pelo usuário."
        ),
        "google_cloud": (
            "Cloud Run, BigQuery, Firestore e Gemini API."
        ),
        "monetization": (
            "Assinatura mensal por empresa."
        ),
        "build_days": 18,
        "technical_fit": 0.90,
        "launch_speed": 0.82,
        "revenue_speed": 0.84,
        "demo_strength": 0.88,
        "novelty": 0.74,
        "operational_risk": 0.38,
        "dependency_risk": 0.28,
    },
    {
        "project_key": "proposal_factory",
        "name": "Proposal Factory AI",
        "category": "Professional Services",
        "problem": (
            "Freelancers e pequenas agências gastam horas preparando "
            "propostas comerciais inconsistentes."
        ),
        "solution": (
            "Gemini transforma briefing, escopo e orçamento em proposta, "
            "cronograma, entregáveis e follow-up comercial."
        ),
        "google_cloud": (
            "Cloud Run, Cloud Storage, Firestore e Gemini API."
        ),
        "monetization": (
            "Créditos por proposta e plano mensal."
        ),
        "build_days": 10,
        "technical_fit": 0.92,
        "launch_speed": 0.98,
        "revenue_speed": 0.88,
        "demo_strength": 0.86,
        "novelty": 0.62,
        "operational_risk": 0.16,
        "dependency_risk": 0.12,
    },
    {
        "project_key": "invoice_recovery",
        "name": "Invoice Recovery AI",
        "category": "Small Business Services",
        "problem": (
            "Prestadores de serviço perdem receita com faturas atrasadas "
            "e acompanhamento manual."
        ),
        "solution": (
            "Agente Gemini organiza faturas, prioriza cobranças e gera "
            "mensagens de acompanhamento para aprovação humana."
        ),
        "google_cloud": (
            "Cloud Run, Cloud Scheduler, Firestore e Gemini API."
        ),
        "monetization": (
            "Assinatura e percentual opcional sobre receita recuperada."
        ),
        "build_days": 13,
        "technical_fit": 0.91,
        "launch_speed": 0.92,
        "revenue_speed": 0.91,
        "demo_strength": 0.85,
        "novelty": 0.70,
        "operational_risk": 0.30,
        "dependency_risk": 0.20,
    },
    {
        "project_key": "local_growth",
        "name": "Local Growth Operator",
        "category": "Entrepreneurship & Job Creation",
        "problem": (
            "Comércios locais não possuem equipe para organizar campanhas, "
            "ofertas e relacionamento com clientes."
        ),
        "solution": (
            "Operador Gemini que cria campanhas, calendário de vendas, "
            "mensagens e análise de desempenho."
        ),
        "google_cloud": (
            "Cloud Run, BigQuery, Firestore e Gemini API."
        ),
        "monetization": (
            "Assinatura mensal por estabelecimento."
        ),
        "build_days": 16,
        "technical_fit": 0.86,
        "launch_speed": 0.86,
        "revenue_speed": 0.82,
        "demo_strength": 0.84,
        "novelty": 0.68,
        "operational_risk": 0.24,
        "dependency_risk": 0.22,
    },
]


def calculate_score(item: dict) -> float:
    positive = (
        item["technical_fit"] * 24
        + item["launch_speed"] * 20
        + item["revenue_speed"] * 22
        + item["demo_strength"] * 18
        + item["novelty"] * 16
    )

    risk_penalty = (
        item["operational_risk"] * 12
        + item["dependency_risk"] * 8
    )

    time_penalty = max(0, item["build_days"] - 14) * 0.6

    return round(
        max(0, min(100, positive - risk_penalty - time_penalty)),
        2,
    )


conn = sqlite3.connect(DATABASE)
conn.row_factory = sqlite3.Row

conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS gemini_xprize_project_candidates (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_key TEXT NOT NULL UNIQUE,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        problem TEXT NOT NULL,
        solution TEXT NOT NULL,
        google_cloud TEXT NOT NULL,
        monetization TEXT NOT NULL,
        build_days INTEGER NOT NULL,
        technical_fit REAL NOT NULL,
        launch_speed REAL NOT NULL,
        revenue_speed REAL NOT NULL,
        demo_strength REAL NOT NULL,
        novelty REAL NOT NULL,
        operational_risk REAL NOT NULL,
        dependency_risk REAL NOT NULL,
        selection_score REAL NOT NULL,
        selection_status TEXT NOT NULL,
        human_approval_required INTEGER NOT NULL DEFAULT 1,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );
    """
)

results = []
now = utc_now()

for item in CANDIDATES:
    score = calculate_score(item)

    result = {
        **item,
        "selection_score": score,
        "selection_status": "candidate",
    }

    results.append(result)

results.sort(
    key=lambda item: (
        -item["selection_score"],
        item["build_days"],
        -item["revenue_speed"],
    )
)

winner = results[0]
winner["selection_status"] = "recommended"

for item in results:
    conn.execute(
        """
        INSERT INTO gemini_xprize_project_candidates (
            project_key,
            name,
            category,
            problem,
            solution,
            google_cloud,
            monetization,
            build_days,
            technical_fit,
            launch_speed,
            revenue_speed,
            demo_strength,
            novelty,
            operational_risk,
            dependency_risk,
            selection_score,
            selection_status,
            human_approval_required,
            created_at,
            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?
        )
        ON CONFLICT(project_key) DO UPDATE SET
            name = excluded.name,
            category = excluded.category,
            problem = excluded.problem,
            solution = excluded.solution,
            google_cloud = excluded.google_cloud,
            monetization = excluded.monetization,
            build_days = excluded.build_days,
            technical_fit = excluded.technical_fit,
            launch_speed = excluded.launch_speed,
            revenue_speed = excluded.revenue_speed,
            demo_strength = excluded.demo_strength,
            novelty = excluded.novelty,
            operational_risk = excluded.operational_risk,
            dependency_risk = excluded.dependency_risk,
            selection_score = excluded.selection_score,
            selection_status = excluded.selection_status,
            updated_at = excluded.updated_at
        """,
        (
            item["project_key"],
            item["name"],
            item["category"],
            item["problem"],
            item["solution"],
            item["google_cloud"],
            item["monetization"],
            item["build_days"],
            item["technical_fit"],
            item["launch_speed"],
            item["revenue_speed"],
            item["demo_strength"],
            item["novelty"],
            item["operational_risk"],
            item["dependency_risk"],
            item["selection_score"],
            item["selection_status"],
            now,
            now,
        ),
    )

conn.commit()

CSV_PATH.parent.mkdir(parents=True, exist_ok=True)
REPORT.parent.mkdir(parents=True, exist_ok=True)

fields = list(results[0].keys())

with CSV_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as file:
    writer = csv.DictWriter(file, fieldnames=fields)
    writer.writeheader()
    writer.writerows(results)

lines = [
    "# Gemini XPRIZE — Project Selection",
    "",
    f"Gerado em: {now}",
    "",
    "Nenhuma inscrição, pagamento ou submissão externa foi realizada.",
    "",
    "## Recomendação",
    "",
    f"### {winner['name']}",
    "",
    f"- Categoria: **{winner['category']}**",
    f"- Score: **{winner['selection_score']}**",
    f"- Prazo estimado de construção: **{winner['build_days']} dias**",
    f"- Problema: {winner['problem']}",
    f"- Solução: {winner['solution']}",
    f"- Google Cloud: {winner['google_cloud']}",
    f"- Monetização: {winner['monetization']}",
    "",
    "## Ranking completo",
    "",
]

for index, item in enumerate(results, 1):
    lines.extend([
        f"### {index}. {item['name']}",
        "",
        f"- Status: **{item['selection_status']}**",
        f"- Categoria: {item['category']}",
        f"- Score: **{item['selection_score']}**",
        f"- Construção: {item['build_days']} dias",
        f"- Velocidade de receita: {item['revenue_speed']}",
        f"- Força da demonstração: {item['demo_strength']}",
        f"- Risco operacional: {item['operational_risk']}",
        f"- Monetização: {item['monetization']}",
        "",
    ])

REPORT.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== GEMINI XPRIZE PROJECT SELECTION =====")
print(f"Candidates: {len(results)}")
print(f"Recommended: {winner['name']}")
print(f"Category: {winner['category']}")
print(f"Score: {winner['selection_score']}")
print(f"Build days: {winner['build_days']}")
print("External action performed: no")

print()
print("===== PROJECT RANKING =====")

for index, item in enumerate(results, 1):
    print()
    print(f"{index}. {item['name']}")
    print(f"   status: {item['selection_status']}")
    print(f"   category: {item['category']}")
    print(f"   score: {item['selection_score']}")
    print(f"   build days: {item['build_days']}")
    print(f"   monetization: {item['monetization']}")

conn.close()
