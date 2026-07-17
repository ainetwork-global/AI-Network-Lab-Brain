from __future__ import annotations

import json
import re
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path.home() / "AI-Network-Lab-Brain" / "01_GLOBAL_REVENUE_BRAIN"

REPOSITORY = (
    Path.home()
    / "Revenue-Workspaces"
    / "SecureBananaLabs-bug-bounty-743"
    / "repository"
)

REPORT = (
    ROOT
    / "12_REPORTS"
    / "LATEST_SECUREBANANA_REPRODUCTION_CANDIDATES.md"
)

STATE = (
    ROOT
    / "00_CURRENT_STATE"
    / "SECUREBANANA_REPRODUCTION_CANDIDATES.json"
)

SKIP_DIRECTORIES = {
    ".git",
    "node_modules",
    ".next",
    "dist",
    "build",
    "coverage",
    ".turbo",
    ".cache",
    "vendor",
    "__pycache__",
}

CODE_EXTENSIONS = {
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".mjs",
    ".cjs",
    ".json",
}

RULES: list[dict[str, Any]] = [
    {
        "key": "route_without_auth",
        "title": "Rota potencialmente exposta sem autenticação",
        "score": 95,
        "patterns": (
            r"\brouter\.(?:get|post|put|patch|delete)\s*\(",
        ),
        "required_any": (
            "router.",
            "app.",
        ),
        "negative_nearby": (
            "authmiddleware",
            "authenticate",
            "requireauth",
            "protect",
            "isAuthenticated",
        ),
        "file_tokens": (
            "route",
            "routes",
        ),
    },
    {
        "key": "raw_body_to_service",
        "title": "Objeto req.body encaminhado sem seleção explícita",
        "score": 82,
        "patterns": (
            r"\breq\.body\b",
        ),
        "required_any": (
            "create",
            "update",
            "service",
        ),
        "negative_nearby": (
            ".parse(",
            "safeParse(",
            "schema.parse",
            "pick(",
        ),
        "file_tokens": (
            "controller",
            "service",
        ),
    },
    {
        "key": "todo_business_logic",
        "title": "Lógica de produção marcada como TODO/FIXME",
        "score": 75,
        "patterns": (
            r"\bTODO\b",
            r"\bFIXME\b",
            r"NotImplemented",
        ),
        "required_any": (),
        "negative_nearby": (),
        "file_tokens": (),
    },
    {
        "key": "unsafe_numeric_range",
        "title": "Validação numérica possivelmente incompleta",
        "score": 72,
        "patterns": (
            r"\bbudgetMin\b",
            r"\bbudgetMax\b",
            r"\bminAmount\b",
            r"\bmaxAmount\b",
            r"\bstartDate\b",
            r"\bendDate\b",
        ),
        "required_any": (
            "zod",
            "schema",
            "validation",
            "controller",
        ),
        "negative_nearby": (
            "refine(",
            "superRefine(",
            "<=",
            ">=",
        ),
        "file_tokens": (),
    },
    {
        "key": "empty_upload_acceptance",
        "title": "Upload possivelmente aceita arquivo vazio ou ausente",
        "score": 80,
        "patterns": (
            r"\breq\.file\b",
            r"\breq\.files\b",
        ),
        "required_any": (
            "upload",
            "file",
        ),
        "negative_nearby": (
            "if (!req.file",
            "if (!req.files",
            "size === 0",
            "size <= 0",
            "length === 0",
        ),
        "file_tokens": (),
    },
    {
        "key": "async_route_error",
        "title": "Handler async possivelmente sem propagação de erro",
        "score": 68,
        "patterns": (
            r"\basync\s*\(",
            r"\basync\s+function\b",
        ),
        "required_any": (
            "router.",
            "controller",
        ),
        "negative_nearby": (
            "try {",
            "catch (",
            "next(error",
            "next(err",
            "asyncHandler",
        ),
        "file_tokens": (),
    },
    {
        "key": "placeholder_success",
        "title": "Resposta de sucesso possivelmente simulada",
        "score": 78,
        "patterns": (
            r"status\s*:\s*[\"']success[\"']",
            r"success\s*:\s*true",
            r"mock",
            r"placeholder",
        ),
        "required_any": (
            "payment",
            "billing",
            "auth",
            "upload",
        ),
        "negative_nearby": (),
        "file_tokens": (),
    },
]

ISSUE_LIKE_TITLES = (
    "require authentication",
    "should require authentication",
    "allows ",
    "accepts ",
    "fails ",
    "incorrect",
    "inconsistency",
    "validation",
    "empty file",
    "test script",
    "async error",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def relative(path: Path) -> str:
    return str(path.relative_to(REPOSITORY)).replace("\\", "/")


def git_output(*args: str) -> str:
    process = subprocess.run(
        ["git", *args],
        cwd=REPOSITORY,
        text=True,
        capture_output=True,
        check=False,
    )

    return process.stdout.strip() if process.returncode == 0 else ""


def candidate_files() -> list[Path]:
    results: list[Path] = []

    for path in REPOSITORY.rglob("*"):
        if not path.is_file():
            continue

        if any(part in SKIP_DIRECTORIES for part in path.parts):
            continue

        if path.suffix.lower() not in CODE_EXTENSIONS:
            continue

        try:
            size = path.stat().st_size
        except OSError:
            continue

        if size <= 0 or size > 500_000:
            continue

        results.append(path)

    return results


def nearby_text(
    lines: list[str],
    index: int,
    radius: int = 8,
) -> str:
    start = max(index - radius, 0)
    end = min(index + radius + 1, len(lines))

    return "\n".join(lines[start:end])


def extract_existing_issue_titles() -> list[str]:
    titles: list[str] = []

    possible_files = [
        REPOSITORY / ".github" / "ISSUE_TEMPLATE",
        REPOSITORY / "issues",
    ]

    for directory in possible_files:
        if not directory.exists():
            continue

        for path in directory.rglob("*"):
            if not path.is_file():
                continue

            try:
                text = path.read_text(
                    encoding="utf-8",
                    errors="ignore",
                )
            except OSError:
                continue

            first_line = next(
                (
                    line.strip("# ").strip()
                    for line in text.splitlines()
                    if line.strip()
                ),
                "",
            )

            if first_line:
                titles.append(first_line.lower())

    return titles


files = candidate_files()
existing_titles = extract_existing_issue_titles()

findings: list[dict[str, Any]] = []
rule_counts: defaultdict[str, int] = defaultdict(int)

for path in files:
    try:
        text = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        continue

    lines = text.splitlines()
    file_name = relative(path)
    lower_file = file_name.lower()
    lower_text = text.lower()

    for rule in RULES:
        if rule["file_tokens"] and not any(
            token.lower() in lower_file
            for token in rule["file_tokens"]
        ):
            continue

        if rule["required_any"] and not any(
            required.lower() in lower_text
            for required in rule["required_any"]
        ):
            continue

        for line_index, line in enumerate(lines):
            matched = False

            for pattern in rule["patterns"]:
                if re.search(pattern, line, re.IGNORECASE):
                    matched = True
                    break

            if not matched:
                continue

            context = nearby_text(
                lines,
                line_index,
            )

            context_lower = context.lower()

            if rule["negative_nearby"] and any(
                negative.lower() in context_lower
                for negative in rule["negative_nearby"]
            ):
                continue

            score = float(rule["score"])

            if "/test" in lower_file or ".test." in lower_file:
                score -= 35

            if "example" in lower_file or "fixture" in lower_file:
                score -= 25

            if len(lines) <= 250:
                score += 5

            finding = {
                "rule_key": rule["key"],
                "candidate_title": rule["title"],
                "file": file_name,
                "line": line_index + 1,
                "score": round(max(score, 0), 2),
                "line_content": re.sub(
                    r"\s+",
                    " ",
                    line.strip(),
                )[:300],
                "context": context[:2500],
                "reproduction_status": "not_tested",
                "duplicate_check_status": "not_verified_online",
                "external_action_performed": False,
            }

            findings.append(finding)
            rule_counts[rule["key"]] += 1

findings.sort(
    key=lambda item: (
        item["score"],
        -item["line"],
    ),
    reverse=True,
)

# Evita dezenas de ocorrências repetidas no mesmo arquivo/regra.
deduplicated: list[dict[str, Any]] = []
seen: set[tuple[str, str]] = set()

for finding in findings:
    identity = (
        finding["rule_key"],
        finding["file"],
    )

    if identity in seen:
        continue

    seen.add(identity)
    deduplicated.append(finding)

top_candidates = deduplicated[:30]

package_files: list[dict[str, Any]] = []

for package_path in REPOSITORY.rglob("package.json"):
    if any(
        part in SKIP_DIRECTORIES
        for part in package_path.parts
    ):
        continue

    try:
        package = json.loads(
            package_path.read_text(
                encoding="utf-8",
                errors="ignore",
            )
        )
    except (OSError, json.JSONDecodeError):
        continue

    package_files.append({
        "file": relative(package_path),
        "name": package.get("name"),
        "scripts": package.get("scripts") or {},
        "dependencies": sorted(
            (package.get("dependencies") or {}).keys()
        ),
        "dev_dependencies": sorted(
            (package.get("devDependencies") or {}).keys()
        ),
    })

state = {
    "generated_at": utc_now(),
    "repository": str(REPOSITORY),
    "branch": git_output("branch", "--show-current"),
    "commit": git_output("rev-parse", "HEAD"),
    "files_analyzed": len(files),
    "findings_total": len(deduplicated),
    "top_candidates": top_candidates,
    "rule_counts": dict(rule_counts),
    "package_files": package_files,
    "existing_local_issue_titles": existing_titles,
    "external_action_performed": False,
    "issue_created": False,
    "fork_created": False,
    "pull_request_created": False,
    "recommended_next_action": (
        "manually_select_one_candidate_for_local_reproduction"
        if top_candidates
        else "do_not_claim_and_search_another_opportunity"
    ),
}

STATE.write_text(
    json.dumps(
        state,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

lines = [
    "# SecureBananaLabs — Reproduction Candidates",
    "",
    f"Gerado em: {state['generated_at']}",
    "",
    "## Regra operacional",
    "",
    "Nenhum achado abaixo está confirmado como bug.",
    "É obrigatório reproduzir localmente antes de criar qualquer issue.",
    "",
    "## Segurança",
    "",
    "- Ação externa realizada: **não**",
    "- Issue criada: **não**",
    "- Fork criado: **não**",
    "- Pull request criado: **não**",
    "",
    "## Repositório",
    "",
    f"- Branch: `{state['branch']}`",
    f"- Commit: `{state['commit']}`",
    f"- Arquivos analisados: **{len(files)}**",
    f"- Candidatos estáticos: **{len(deduplicated)}**",
    "",
    "## Scripts disponíveis",
    "",
]

for package in package_files:
    lines.extend([
        f"### `{package['file']}`",
        "",
        f"- Pacote: `{package['name']}`",
    ])

    scripts = package["scripts"]

    if scripts:
        for name, command in scripts.items():
            lines.append(
                f"- `{name}` → `{command}`"
            )
    else:
        lines.append("- Nenhum script definido.")

    lines.append("")

lines.extend([
    "## Candidatos para reprodução local",
    "",
])

if not top_candidates:
    lines.append(
        "Nenhum candidato estático suficientemente claro foi encontrado."
    )

for index, finding in enumerate(top_candidates, 1):
    lines.extend([
        f"### {index}. {finding['candidate_title']}",
        "",
        f"- Arquivo: `{finding['file']}`",
        f"- Linha aproximada: **{finding['line']}**",
        f"- Score estático: **{finding['score']}**",
        f"- Regra: `{finding['rule_key']}`",
        f"- Reprodução: **não realizada**",
        f"- Duplicidade online: **não verificada**",
        "",
        "Trecho:",
        "",
        "```text",
        finding["line_content"],
        "```",
        "",
        "Próximo teste local:",
        "",
        "1. Ler o arquivo e identificar a intenção da função.",
        "2. Criar um teste mínimo que falhe no comportamento atual.",
        "3. Confirmar que o teste falha antes de qualquer correção.",
        "4. Verificar se o mesmo problema já foi reportado.",
        "5. Somente então preparar uma proposta de correção.",
        "",
    ])

lines.extend([
    "## Decisão",
    "",
    (
        "**Selecionar apenas um candidato para reprodução local. "
        "Não criar issue enquanto não houver teste falhando e "
        "checagem de duplicidade.**"
    ),
])

REPORT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print("===== REPRODUCTION CANDIDATE ANALYSIS =====")
print("Repository:", REPOSITORY)
print("Branch:", state["branch"])
print("Commit:", state["commit"])
print("Files analyzed:", len(files))
print("Static candidates:", len(deduplicated))
print("Top candidates:", len(top_candidates))

print()
print("===== TOP REPRODUCTION CANDIDATES =====")

for index, finding in enumerate(top_candidates[:15], 1):
    print()
    print(f"{index}. {finding['candidate_title']}")
    print("   file:", finding["file"])
    print("   line:", finding["line"])
    print("   score:", finding["score"])
    print("   rule:", finding["rule_key"])
    print("   reproduction:", "not_tested")
    print("   duplicate check:", "not_verified_online")

print()
print("===== SAFETY STATUS =====")
print("External action performed: no")
print("Issue created: no")
print("Fork created: no")
print("Pull request created: no")
print(
    "Recommended next action:",
    state["recommended_next_action"],
)
print("Report:", REPORT)
