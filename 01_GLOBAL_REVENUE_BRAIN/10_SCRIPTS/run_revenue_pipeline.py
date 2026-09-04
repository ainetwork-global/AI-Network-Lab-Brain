from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON = sys.executable
HEALTH = PROJECT_ROOT / "00_CURRENT_STATE" / "PIPELINE_HEALTH.json"
HEALTH_REPORT = PROJECT_ROOT / "12_REPORTS" / "LATEST_PIPELINE_HEALTH.md"
RESULTS: list[dict[str, object]] = []


def run_step(name: str, script_path: Path, *, critical: bool = False) -> None:
    print("")
    print("=" * 70)
    print(name)
    print("=" * 70)

    try:
        result = subprocess.run(
            [PYTHON, str(script_path)],
            cwd=PROJECT_ROOT,
            text=True,
            check=False,
            timeout=600,
        )
    except (subprocess.TimeoutExpired, OSError) as error:
        RESULTS.append({
            "name": name, "script": str(script_path), "returncode": -1,
            "critical": critical, "stdout_tail": "", "stderr_tail": str(error),
        })
        if critical:
            raise RuntimeError(f"Etapa crítica falhou: {name}: {error}") from error
        print(f"Fonte indisponível; ciclo continuará: {name}: {error}")
        return
    RESULTS.append({
        "name": name,
        "script": str(script_path.relative_to(PROJECT_ROOT.parent)),
        "returncode": result.returncode,
        "critical": critical,
        "stdout_tail": result.stdout[-2000:] if result.stdout else "",
        "stderr_tail": result.stderr[-2000:] if result.stderr else "",
    })
    if result.returncode != 0 and critical:
        raise RuntimeError(
            f"Etapa falhou: {name}. Código: {result.returncode}"
        )
    if result.returncode != 0:
        print(f"Fonte indisponível; ciclo continuará: {name}")


def write_health(started_at: datetime) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "started_at": started_at.isoformat(),
        "status": "healthy" if all(item["returncode"] == 0 for item in RESULTS) else "degraded",
        "successful_steps": sum(item["returncode"] == 0 for item in RESULTS),
        "failed_steps": sum(item["returncode"] != 0 for item in RESULTS),
        "steps": RESULTS,
    }
    HEALTH.parent.mkdir(parents=True, exist_ok=True)
    HEALTH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    lines = [
        "# PIPELINE HEALTH", "", f"Generated: `{payload['generated_at']}`", "",
        f"- Status: **{payload['status']}**",
        f"- Successful steps: **{payload['successful_steps']}**",
        f"- Failed steps: **{payload['failed_steps']}**", "",
        "| Step | Result | Critical |", "|---|---:|---|",
    ]
    for item in RESULTS:
        lines.append(f"| {item['name']} | {item['returncode']} | {item['critical']} |")
    HEALTH_REPORT.parent.mkdir(parents=True, exist_ok=True)
    HEALTH_REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    started_at = datetime.now(timezone.utc)

    print("")
    print("GLOBAL REVENUE BRAIN")
    print("PIPELINE AUTÔNOMO DE DESCOBERTA E PRIORIZAÇÃO")
    print(f"Início UTC: {started_at.isoformat()}")

    run_step(
        "1. Inicialização do banco local",
        PROJECT_ROOT / "10_SCRIPTS" / "database.py",
        critical=True,
    )

    run_step(
        "2. Descoberta global de oportunidades",
        PROJECT_ROOT
        / "02_DISCOVERY"
        / "global_revenue_hunter.py",
    )

    run_step(
        "3. Descoberta global de trabalhos remotos pagos",
        PROJECT_ROOT
        / "02_DISCOVERY"
        / "global_paid_work_discovery.py",
    )

    run_step(
        "4. Descoberta oficial de hackathons Devpost",
        PROJECT_ROOT
        / "02_DISCOVERY"
        / "devpost_official_adapter.py",
    )

    run_step(
        "5. Descoberta de Grants.gov e Immunefi",
        PROJECT_ROOT
        / "02_DISCOVERY"
        / "official_source_adapters.py",
    )

    run_step(
        "6. Descoberta oficial de projetos Superteam",
        PROJECT_ROOT.parent
        / "02_DISCOVERY"
        / "superteam_earn_official_adapter.py",
    )

    run_step(
        "7. Descoberta oficial de bounties Algora",
        PROJECT_ROOT
        / "02_DISCOVERY"
        / "algora_open_bounty_adapter.py",
    )

    run_step(
        "8. Integração Algora na fila principal",
        PROJECT_ROOT
        / "02_DISCOVERY"
        / "import_algora_into_opportunities.py",
    )

    run_step(
        "9. Integração das plataformas globais na fila principal",
        PROJECT_ROOT
        / "02_DISCOVERY"
        / "import_global_sources_into_opportunities.py",
    )

    run_step(
        "10. Monitoramento de plataformas com conta",
        PROJECT_ROOT
        / "02_DISCOVERY"
        / "participant_platform_monitor.py",
    )

    run_step(
        "11. Geração da fila financeira prioritária",
        PROJECT_ROOT
        / "03_INTELLIGENCE"
        / "generate_revenue_report.py",
        critical=True,
    )

    completed_at = datetime.now(timezone.utc)
    duration = (completed_at - started_at).total_seconds()
    write_health(started_at)

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
