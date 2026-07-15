from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable


def run_step(name: str, script_path: Path) -> None:
    print("")
    print("=" * 70)
    print(name)
    print("=" * 70)

    result = subprocess.run(
        [PYTHON, str(script_path)],
        cwd=PROJECT_ROOT,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"Etapa falhou: {name}. Código: {result.returncode}"
        )


def main() -> int:
    started_at = datetime.now(timezone.utc)

    print("")
    print("GLOBAL REVENUE BRAIN")
    print("PIPELINE AUTÔNOMO DE DESCOBERTA E PRIORIZAÇÃO")
    print(f"Início UTC: {started_at.isoformat()}")

    run_step(
        "1. Inicialização do banco local",
        PROJECT_ROOT / "10_SCRIPTS" / "database.py",
    )

    run_step(
        "2. Descoberta global de oportunidades",
        PROJECT_ROOT
        / "02_DISCOVERY"
        / "global_revenue_hunter.py",
    )

    run_step(
        "3. Geração da fila financeira prioritária",
        PROJECT_ROOT
        / "03_INTELLIGENCE"
        / "generate_revenue_report.py",
    )

    completed_at = datetime.now(timezone.utc)
    duration = (completed_at - started_at).total_seconds()

    print("")
    print("=" * 70)
    print("PIPELINE CONCLUÍDO")
    print("=" * 70)
    print(f"Fim UTC: {completed_at.isoformat()}")
    print(f"Duração: {duration:.2f} segundos")
    print("")
    print(
        "Relatório: "
        + str(
            PROJECT_ROOT
            / "12_REPORTS"
            / "LATEST_REVENUE_OPPORTUNITIES.md"
        )
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
