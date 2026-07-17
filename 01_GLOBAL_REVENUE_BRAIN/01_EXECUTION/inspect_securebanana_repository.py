from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


BRAIN_ROOT = (
    Path.home()
    / "AI-Network-Lab-Brain"
)

PROJECT_ROOT = (
    BRAIN_ROOT
    / "01_GLOBAL_REVENUE_BRAIN"
)

REPOSITORY = (
    Path.home()
    / "Revenue-Workspaces"
    / "SecureBananaLabs-bug-bounty-743"
    / "repository"
)

REPORT = (
    PROJECT_ROOT
    / "12_REPORTS"
    / "LATEST_SECUREBANANA_LOCAL_INSPECTION.md"
)

STATE_FILE = (
    PROJECT_ROOT
    / "00_CURRENT_STATE"
    / "SECUREBANANA_743_INSPECTION_STATE.json"
)

SKIP_DIRECTORIES = {
    ".git",
    ".github",
    ".idea",
    ".vscode",
    "node_modules",
    ".venv",
    "venv",
    "__pycache__",
    "dist",
    "build",
    "coverage",
    ".next",
    "target",
    "vendor",
}

TEXT_EXTENSIONS = {
    ".py",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".json",
    ".md",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".html",
    ".css",
    ".scss",
    ".sql",
    ".sh",
    ".ps1",
    ".go",
    ".rs",
    ".java",
    ".cs",
    ".php",
    ".rb",
}

LANGUAGES = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript/React",
    ".ts": "TypeScript",
    ".tsx": "TypeScript/React",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".cs": "C#",
    ".php": "PHP",
    ".rb": "Ruby",
    ".ps1": "PowerShell",
    ".sh": "Shell",
    ".sql": "SQL",
    ".html": "HTML",
    ".css": "CSS",
    ".scss": "SCSS",
}

SIGNALS = (
    "TODO",
    "FIXME",
    "HACK",
    "XXX",
    "NotImplemented",
    "NotImplementedError",
    "pass",
    "console.log",
    "print(",
)

TEST_PATTERNS = (
    "test_",
    "_test.",
    ".spec.",
    ".test.",
    "tests",
    "__tests__",
)

CONFIG_FILES = (
    "package.json",
    "pyproject.toml",
    "requirements.txt",
    "setup.py",
    "Cargo.toml",
    "go.mod",
    "pom.xml",
    "Dockerfile",
    "docker-compose.yml",
    "Makefile",
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def run_git(*arguments: str) -> str:
    process = subprocess.run(
        ["git", *arguments],
        cwd=REPOSITORY,
        text=True,
        capture_output=True,
        check=False,
    )

    if process.returncode != 0:
        return ""

    return process.stdout.strip()


def relative(path: Path) -> str:
    return str(
        path.relative_to(REPOSITORY)
    ).replace("\\", "/")


def readable_files() -> list[Path]:
    results: list[Path] = []

    for path in REPOSITORY.rglob("*"):
        if not path.is_file():
            continue

        if any(
            part in SKIP_DIRECTORIES
            for part in path.parts
        ):
            continue

        if path.suffix.lower() not in TEXT_EXTENSIONS:
            continue

        try:
            if path.stat().st_size > 1_000_000:
                continue
        except OSError:
            continue

        results.append(path)

    return results


if not (REPOSITORY / ".git").exists():
    raise RuntimeError(
        f"Repositório não encontrado: {REPOSITORY}"
    )

files = readable_files()

extension_counts = Counter(
    path.suffix.lower()
    for path in files
)

language_counts = Counter()

for extension, total in extension_counts.items():
    language = LANGUAGES.get(extension)

    if language:
        language_counts[language] += total

signals: list[dict[str, object]] = []
test_files: list[str] = []
candidate_files: list[dict[str, object]] = []

for path in files:
    path_text = relative(path)
    lowered_path = path_text.lower()

    if any(
        pattern in lowered_path
        for pattern in TEST_PATTERNS
    ):
        test_files.append(path_text)

    try:
        content = path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        continue

    lines = content.splitlines()
    signal_count = 0

    for line_number, line in enumerate(lines, 1):
        for signal in SIGNALS:
            if signal.lower() not in line.lower():
                continue

            stripped = re.sub(
                r"\s+",
                " ",
                line.strip(),
            )

            signals.append({
                "file": path_text,
                "line": line_number,
                "signal": signal,
                "content": stripped[:240],
            })

            signal_count += 1

            if len(signals) >= 300:
                break

        if len(signals) >= 300:
            break

    score = 0.0
    reasons: list[str] = []

    if signal_count:
        score += min(signal_count * 8, 40)
        reasons.append(
            f"{signal_count} marcador(es) de manutenção"
        )

    if len(lines) <= 250:
        score += 20
        reasons.append("arquivo de escopo pequeno")
    elif len(lines) <= 600:
        score += 10
        reasons.append("arquivo de escopo médio")

    if path.suffix.lower() in {
        ".py",
        ".js",
        ".ts",
        ".tsx",
        ".jsx",
        ".ps1",
    }:
        score += 15
        reasons.append("arquivo executável ou de lógica")

    filename_lower = path.name.lower()

    if any(
        token in filename_lower
        for token in (
            "util",
            "helper",
            "parser",
            "validator",
            "config",
            "script",
        )
    ):
        score += 10
        reasons.append("componente potencialmente isolado")

    if any(
        token in lowered_path
        for token in (
            "example",
            "fixture",
            "vendor",
            "generated",
            "lock",
        )
    ):
        score -= 30

    if score > 0:
        candidate_files.append({
            "file": path_text,
            "score": round(score, 2),
            "lines": len(lines),
            "signals": signal_count,
            "reasons": reasons,
        })

candidate_files.sort(
    key=lambda item: (
        item["score"],
        -item["lines"],
    ),
    reverse=True,
)

config_found = [
    name
    for name in CONFIG_FILES
    if (REPOSITORY / name).exists()
]

readme_files = sorted(
    relative(path)
    for path in REPOSITORY.glob("README*")
    if path.is_file()
)

branch = run_git(
    "branch",
    "--show-current",
)

commit = run_git(
    "rev-parse",
    "HEAD",
)

remote = run_git(
    "remote",
    "get-url",
    "origin",
)

state = {
    "generated_at": utc_now(),
    "repository": str(REPOSITORY),
    "remote": remote,
    "branch": branch,
    "commit": commit,
    "files_analyzed": len(files),
    "languages": dict(language_counts),
    "test_files": test_files,
    "signals": signals,
    "candidate_files": candidate_files[:50],
    "external_action_performed": False,
    "issue_created": False,
    "fork_created": False,
    "pull_request_created": False,
}

STATE_FILE.parent.mkdir(
    parents=True,
    exist_ok=True,
)

STATE_FILE.write_text(
    json.dumps(
        state,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

lines = [
    "# SecureBananaLabs #743 — Local Repository Inspection",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "## Segurança operacional",
    "",
    "- Inspeção somente local: **sim**",
    "- Issue criada: **não**",
    "- Comentário publicado: **não**",
    "- Fork criado: **não**",
    "- Pull request criado: **não**",
    "- Código externo submetido: **não**",
    "",
    "## Repositório",
    "",
    f"- Remote: `{remote}`",
    f"- Branch: `{branch}`",
    f"- Commit analisado: `{commit}`",
    f"- Arquivos de texto/código analisados: **{len(files)}**",
    "",
    "## Tecnologias encontradas",
    "",
]

if language_counts:
    for language, total in language_counts.most_common():
        lines.append(
            f"- {language}: {total} arquivo(s)"
        )
else:
    lines.append(
        "- Nenhuma linguagem principal detectada."
    )

lines.extend([
    "",
    "## Arquivos de configuração",
    "",
])

if config_found:
    lines.extend(
        f"- `{name}`"
        for name in config_found
    )
else:
    lines.append(
        "- Nenhum arquivo de configuração principal detectado."
    )

lines.extend([
    "",
    "## READMEs",
    "",
])

if readme_files:
    lines.extend(
        f"- `{name}`"
        for name in readme_files
    )
else:
    lines.append("- Nenhum README encontrado.")

lines.extend([
    "",
    "## Testes encontrados",
    "",
])

if test_files:
    lines.extend(
        f"- `{name}`"
        for name in test_files[:100]
    )
else:
    lines.append(
        "- Nenhum arquivo de teste identificado pelo nome."
    )

lines.extend([
    "",
    "## Marcadores de possível manutenção",
    "",
])

if signals:
    for item in signals[:100]:
        lines.append(
            f"- `{item['file']}:{item['line']}` — "
            f"`{item['signal']}` — {item['content']}"
        )
else:
    lines.append(
        "- Nenhum TODO/FIXME ou marcador equivalente encontrado."
    )

lines.extend([
    "",
    "## Arquivos candidatos para inspeção detalhada",
    "",
])

if candidate_files:
    for index, item in enumerate(
        candidate_files[:30],
        1,
    ):
        lines.extend([
            f"### {index}. `{item['file']}`",
            "",
            f"- Score de inspeção: **{item['score']}**",
            f"- Linhas: {item['lines']}",
            f"- Marcadores: {item['signals']}",
            (
                "- Motivos: "
                + ", ".join(item["reasons"])
            ),
            "",
        ])
else:
    lines.append(
        "Nenhum arquivo candidato foi identificado."
    )

lines.extend([
    "## Próximo gate",
    "",
    (
        "Escolher um único comportamento pequeno, reproduzível "
        "e testável. Nenhuma issue deverá ser criada antes de "
        "existir reprodução local e proposta técnica objetiva."
    ),
])

REPORT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print("===== SECUREBANANA LOCAL INSPECTION =====")
print("Repository:", REPOSITORY)
print("Branch:", branch)
print("Commit:", commit)
print("Files analyzed:", len(files))
print("Test files:", len(test_files))
print("Maintenance signals:", len(signals))
print(
    "Candidate files:",
    len(candidate_files),
)

print()
print("===== TOP LOCAL INSPECTION CANDIDATES =====")

for index, item in enumerate(
    candidate_files[:15],
    1,
):
    print()
    print(f"{index}. {item['file']}")
    print("   score:", item["score"])
    print("   lines:", item["lines"])
    print("   signals:", item["signals"])
    print(
        "   reasons:",
        ", ".join(item["reasons"]),
    )

print()
print("External action performed: no")
print("Issue created: no")
print("Fork created: no")
print("Pull request created: no")
print("Report:", REPORT)
