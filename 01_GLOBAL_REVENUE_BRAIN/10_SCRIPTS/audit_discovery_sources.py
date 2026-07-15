from __future__ import annotations

import ast
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

CONFIG_FILE = ROOT / "01_CONFIG" / "hunter_sources.json"
HUNTER_FILE = ROOT / "02_DISCOVERY" / "global_revenue_hunter.py"
SCANNER_FILE = ROOT / "02_DISCOVERY" / "global_opportunity_scanner.py"
PIPELINE_FILE = ROOT / "10_SCRIPTS" / "run_revenue_pipeline.py"
DATABASE_FILE = ROOT / "11_DATA" / "global_revenue_brain.db"
REPORT_FILE = ROOT / "12_REPORTS" / "LATEST_DISCOVERY_SOURCE_AUDIT.md"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_json(path: Path) -> Any:
    if not path.exists():
        return None

    return json.loads(path.read_text(encoding="utf-8-sig"))


def function_names(path: Path) -> list[str]:
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(content)

    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]


def imported_modules(path: Path) -> list[str]:
    if not path.exists():
        return []

    content = path.read_text(encoding="utf-8-sig")
    tree = ast.parse(content)
    modules: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                modules.add(alias.name)

        elif isinstance(node, ast.ImportFrom):
            if node.module:
                modules.add(node.module)

    return sorted(modules)


def summarize_config(value: Any, prefix: str = "") -> list[str]:
    lines: list[str] = []

    if isinstance(value, dict):
        for key, item in value.items():
            current = f"{prefix}.{key}" if prefix else str(key)

            if isinstance(item, list):
                lines.append(f"- `{current}`: lista com {len(item)} itens")

                for index, entry in enumerate(item[:30], start=1):
                    if isinstance(entry, dict):
                        name = (
                            entry.get("name")
                            or entry.get("source")
                            or entry.get("query")
                            or entry.get("url")
                            or entry.get("endpoint")
                            or str(entry)
                        )
                        lines.append(f"  - {index}. {name}")
                    else:
                        lines.append(f"  - {index}. {entry}")

            elif isinstance(item, dict):
                lines.append(f"- `{current}`: objeto com {len(item)} campos")
                lines.extend(summarize_config(item, current))

            else:
                lines.append(f"- `{current}`: `{item}`")

    elif isinstance(value, list):
        lines.append(f"- Lista raiz com {len(value)} itens")

    else:
        lines.append(f"- Valor raiz: `{value}`")

    return lines


def database_source_summary() -> list[sqlite3.Row]:
    if not DATABASE_FILE.exists():
        return []

    connection = sqlite3.connect(DATABASE_FILE)
    connection.row_factory = sqlite3.Row

    try:
        tables = {
            row["name"]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table'
                """
            ).fetchall()
        }

        if "opportunities" not in tables:
            return []

        columns = {
            row["name"]
            for row in connection.execute(
                "PRAGMA table_info(opportunities)"
            ).fetchall()
        }

        source_column = None

        for candidate in ("source_name", "source", "platform"):
            if candidate in columns:
                source_column = candidate
                break

        if not source_column:
            return []

        query = f"""
            SELECT
                COALESCE("{source_column}", 'unknown') AS source,
                COUNT(*) AS total
            FROM opportunities
            GROUP BY COALESCE("{source_column}", 'unknown')
            ORDER BY total DESC, source
        """

        return connection.execute(query).fetchall()

    finally:
        connection.close()


config = read_json(CONFIG_FILE)

hunter_functions = function_names(HUNTER_FILE)
scanner_functions = function_names(SCANNER_FILE)
pipeline_functions = function_names(PIPELINE_FILE)

hunter_imports = imported_modules(HUNTER_FILE)
scanner_imports = imported_modules(SCANNER_FILE)

source_rows = database_source_summary()

lines = [
    "# Global Revenue Brain — Auditoria das Fontes de Descoberta",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Arquivos encontrados",
    "",
    f"- hunter_sources.json: **{'sim' if CONFIG_FILE.exists() else 'não'}**",
    f"- global_revenue_hunter.py: **{'sim' if HUNTER_FILE.exists() else 'não'}**",
    f"- global_opportunity_scanner.py: **{'sim' if SCANNER_FILE.exists() else 'não'}**",
    f"- run_revenue_pipeline.py: **{'sim' if PIPELINE_FILE.exists() else 'não'}**",
    f"- global_revenue_brain.db: **{'sim' if DATABASE_FILE.exists() else 'não'}**",
    "",
    "## Estrutura atual do hunter_sources.json",
    "",
]

if config is None:
    lines.append("Arquivo não encontrado.")
else:
    lines.extend(summarize_config(config))

lines.extend([
    "",
    "## Funções do Global Revenue Hunter",
    "",
])

if hunter_functions:
    lines.extend(f"- `{name}`" for name in hunter_functions)
else:
    lines.append("Nenhuma função encontrada ou arquivo ausente.")

lines.extend([
    "",
    "## Bibliotecas utilizadas pelo Global Revenue Hunter",
    "",
])

if hunter_imports:
    lines.extend(f"- `{name}`" for name in hunter_imports)
else:
    lines.append("Nenhum import encontrado.")

lines.extend([
    "",
    "## Funções do scanner RSS inicial",
    "",
])

if scanner_functions:
    lines.extend(f"- `{name}`" for name in scanner_functions)
else:
    lines.append("Nenhuma função encontrada ou arquivo ausente.")

lines.extend([
    "",
    "## Bibliotecas utilizadas pelo scanner RSS",
    "",
])

if scanner_imports:
    lines.extend(f"- `{name}`" for name in scanner_imports)
else:
    lines.append("Nenhum import encontrado.")

lines.extend([
    "",
    "## Funções do pipeline principal",
    "",
])

if pipeline_functions:
    lines.extend(f"- `{name}`" for name in pipeline_functions)
else:
    lines.append("Nenhuma função encontrada ou arquivo ausente.")

lines.extend([
    "",
    "## Registros atuais por fonte",
    "",
])

if source_rows:
    for row in source_rows:
        lines.append(f"- {row['source']}: **{row['total']}**")
else:
    lines.append("Não foi possível obter a distribuição por fonte.")

REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
REPORT_FILE.write_text("\n".join(lines), encoding="utf-8")

print()
print("===== DISCOVERY SOURCE AUDIT =====")
print(f"Config encontrada: {CONFIG_FILE.exists()}")
print(f"Hunter encontrado: {HUNTER_FILE.exists()}")
print(f"Scanner encontrado: {SCANNER_FILE.exists()}")
print(f"Pipeline encontrado: {PIPELINE_FILE.exists()}")

print()
print("===== CONFIG STRUCTURE =====")

if config is None:
    print("hunter_sources.json não encontrado")
else:
    for line in summarize_config(config):
        print(line)

print()
print("===== HUNTER FUNCTIONS =====")

for name in hunter_functions:
    print(name)

print()
print("===== CURRENT SOURCES IN DATABASE =====")

for row in source_rows:
    print(f"{row['source']}: {row['total']}")

print()
print(f"Relatório salvo em: {REPORT_FILE}")
