from __future__ import annotations

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
REPORT_PATH = (
    PROJECT_ROOT
    / "12_REPORTS"
    / "LATEST_REVENUE_OPPORTUNITIES.md"
)
CSV_PATH = (
    PROJECT_ROOT
    / "04_OPPORTUNITIES"
    / "priority_opportunities.csv"
)

sys.path.insert(0, str(PROJECT_ROOT / "10_SCRIPTS"))

from database import connect


def money(value, currency: str | None) -> str:
    if value is None:
        return "não identificado"

    return f"{currency or 'USD'} {float(value):,.2f}"


def generate_report() -> None:
    generated_at = datetime.now(timezone.utc).isoformat()

    with connect() as database:
        totals = database.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN final_score >= 55 THEN 1 ELSE 0 END)
                    AS priority_total,
                SUM(CASE WHEN final_score >= 25 THEN 1 ELSE 0 END)
                    AS review_total,
                SUM(CASE WHEN risk_score >= 40 THEN 1 ELSE 0 END)
                    AS risk_total,
                MAX(final_score) AS maximum_score
            FROM opportunities
            """
        ).fetchone()

        rows = database.execute(
            """
            SELECT
                opportunity_key,
                title,
                category,
                source_name,
                source_url,
                repository,
                author,
                estimated_value,
                currency,
                financial_score,
                confidence_score,
                automation_score,
                risk_score,
                final_score,
                score_reason,
                status,
                discovered_at
            FROM opportunities
            WHERE final_score >= 25
              AND risk_score < 60
            ORDER BY
                final_score DESC,
                estimated_value DESC,
                discovered_at DESC
            LIMIT 50
            """
        ).fetchall()

        source_rows = database.execute(
            """
            SELECT
                source_name,
                source_type,
                last_checked_at,
                last_success_at,
                consecutive_errors,
                last_items_found,
                last_error
            FROM source_health
            ORDER BY
                consecutive_errors ASC,
                last_items_found DESC,
                source_name ASC
            """
        ).fetchall()

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    lines: list[str] = [
        "# Global Revenue Hunter — Relatório Executivo",
        "",
        f"Gerado em: `{generated_at}`",
        "",
        "## Resumo",
        "",
        f"- Oportunidades armazenadas: **{totals['total'] or 0}**",
        f"- Oportunidades prioritárias: **{totals['priority_total'] or 0}**",
        f"- Oportunidades para revisão: **{totals['review_total'] or 0}**",
        f"- Oportunidades com risco elevado: **{totals['risk_total'] or 0}**",
        f"- Maior score encontrado: **{float(totals['maximum_score'] or 0):.2f}**",
        "",
        "## Fila prioritária",
        "",
    ]

    if not rows:
        lines.extend(
            [
                "Nenhuma oportunidade atingiu o score mínimo nesta execução.",
                "",
            ]
        )

    for index, row in enumerate(rows, start=1):
        lines.extend(
            [
                f"### {index}. {row['title']}",
                "",
                f"- **Score final:** {row['final_score']}",
                f"- **Categoria:** {row['category']}",
                f"- **Fonte:** {row['source_name']}",
                f"- **Valor estimado:** {money(row['estimated_value'], row['currency'])}",
                f"- **Score financeiro:** {row['financial_score']}",
                f"- **Confiança:** {row['confidence_score']}",
                f"- **Automação:** {row['automation_score']}",
                f"- **Risco:** {row['risk_score']}",
                f"- **Repositório:** {row['repository'] or '-'}",
                f"- **Autor:** {row['author'] or '-'}",
                f"- **URL:** {row['source_url']}",
                f"- **Justificativa:** {row['score_reason'] or '-'}",
                "",
            ]
        )

    lines.extend(
        [
            "## Saúde das fontes",
            "",
            "| Fonte | Tipo | Itens | Erros consecutivos | Último sucesso |",
            "|---|---:|---:|---:|---|",
        ]
    )

    for source in source_rows:
        lines.append(
            "| "
            + f"{source['source_name']} | "
            + f"{source['source_type']} | "
            + f"{source['last_items_found']} | "
            + f"{source['consecutive_errors']} | "
            + f"{source['last_success_at'] or '-'} |"
        )

    REPORT_PATH.write_text(
        "\n".join(lines),
        encoding="utf-8",
    )

    fieldnames = [
        "opportunity_key",
        "title",
        "category",
        "source_name",
        "source_url",
        "repository",
        "author",
        "estimated_value",
        "currency",
        "financial_score",
        "confidence_score",
        "automation_score",
        "risk_score",
        "final_score",
        "status",
        "discovered_at",
    ]

    with CSV_PATH.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for row in rows:
            writer.writerow(
                {
                    field: row[field]
                    for field in fieldnames
                }
            )

    print(f"Relatório criado: {REPORT_PATH}")
    print(f"Fila CSV criada: {CSV_PATH}")
    print(f"Oportunidades na fila: {len(rows)}")


if __name__ == "__main__":
    generate_report()
