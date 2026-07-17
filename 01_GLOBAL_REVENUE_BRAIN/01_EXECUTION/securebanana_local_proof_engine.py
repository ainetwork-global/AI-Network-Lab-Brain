from __future__ import annotations

import json
import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = (
    Path.home()
    / "AI-Network-Lab-Brain"
    / "01_GLOBAL_REVENUE_BRAIN"
)

REPOSITORY = (
    Path.home()
    / "Revenue-Workspaces"
    / "SecureBananaLabs-bug-bounty-743"
    / "repository"
)

CANDIDATES_STATE = (
    ROOT
    / "00_CURRENT_STATE"
    / "SECUREBANANA_REPRODUCTION_CANDIDATES.json"
)

PROOF_STATE = (
    ROOT
    / "00_CURRENT_STATE"
    / "SECUREBANANA_LOCAL_PROOF_STATE.json"
)

REPORT = (
    ROOT
    / "12_REPORTS"
    / "LATEST_SECUREBANANA_LOCAL_PROOF.md"
)

PROOF_WORKSPACE = (
    Path.home()
    / "Revenue-Workspaces"
    / "SecureBananaLabs-bug-bounty-743"
    / "proof"
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def relative(path: Path) -> str:
    return str(
        path.relative_to(REPOSITORY)
    ).replace("\\", "/")


def run_command(
    command: list[str],
    *,
    cwd: Path,
    timeout: int = 120,
) -> dict[str, Any]:
    try:
        process = subprocess.run(
            command,
            cwd=cwd,
            text=True,
            capture_output=True,
            timeout=timeout,
            check=False,
        )

        return {
            "command": command,
            "return_code": process.returncode,
            "stdout": (process.stdout or "")[-10000:],
            "stderr": (process.stderr or "")[-10000:],
            "timed_out": False,
        }

    except subprocess.TimeoutExpired as error:
        return {
            "command": command,
            "return_code": None,
            "stdout": (
                error.stdout.decode()
                if isinstance(error.stdout, bytes)
                else str(error.stdout or "")
            )[-10000:],
            "stderr": (
                error.stderr.decode()
                if isinstance(error.stderr, bytes)
                else str(error.stderr or "")
            )[-10000:],
            "timed_out": True,
        }


def read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return ""


def find_import_target(
    source_file: Path,
    import_path: str,
) -> Path | None:
    if not import_path.startswith("."):
        return None

    base = (
        source_file.parent
        / import_path
    ).resolve()

    candidates = [
        base,
        base.with_suffix(".js"),
        base.with_suffix(".mjs"),
        base.with_suffix(".cjs"),
        base / "index.js",
    ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return candidate

    return None


def collect_related_files(
    source_file: Path,
    source_text: str,
) -> list[Path]:
    related: list[Path] = []

    patterns = (
        re.compile(
            r"""require\(\s*["']([^"']+)["']\s*\)"""
        ),
        re.compile(
            r"""from\s+["']([^"']+)["']"""
        ),
    )

    for pattern in patterns:
        for match in pattern.finditer(source_text):
            target = find_import_target(
                source_file,
                match.group(1),
            )

            if target and target not in related:
                related.append(target)

    return related


def detect_full_body_forwarding(
    text: str,
) -> list[str]:
    patterns = (
        r"\w+\s*\(\s*req\.body\s*\)",
        r"\w+\.\w+\s*\(\s*req\.body\s*\)",
        r"\{\s*\.\.\.req\.body\s*\}",
        r"Object\.assign\s*\([^)]*req\.body",
    )

    matches: list[str] = []

    for pattern in patterns:
        for match in re.finditer(
            pattern,
            text,
            re.IGNORECASE,
        ):
            matches.append(
                re.sub(
                    r"\s+",
                    " ",
                    match.group(0),
                )[:400]
            )

    return matches


def detect_validation_guards(
    text: str,
) -> list[str]:
    terms = (
        "schema.parse",
        "safeParse",
        ".validate(",
        "validationResult",
        "matchedData",
        "pick(",
        "sanitize",
        "allowedFields",
        "whitelist",
    )

    return [
        term
        for term in terms
        if term.lower() in text.lower()
    ]


def detect_upload_guards(
    text: str,
) -> list[str]:
    patterns = (
        r"if\s*\(\s*!\s*req\.file",
        r"if\s*\(\s*!\s*req\.files",
        r"req\.file\?\.size",
        r"req\.file\.size\s*(?:===|<=)\s*0",
        r"req\.files\.length\s*(?:===|<=)\s*0",
        r"if\s*\(\s*req\.file",
    )

    matches: list[str] = []

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            matches.append(
                match.group(0)
            )

    return matches


def detect_cross_field_validation(
    text: str,
) -> list[str]:
    patterns = (
        r"\.refine\s*\(",
        r"\.superRefine\s*\(",
        r"budgetMin\s*<=\s*budgetMax",
        r"budgetMax\s*>=\s*budgetMin",
        r"startDate\s*<=\s*endDate",
        r"endDate\s*>=\s*startDate",
    )

    matches: list[str] = []

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE,
        )

        if match:
            matches.append(
                match.group(0)
            )

    return matches


def detect_placeholder_file(
    text: str,
) -> dict[str, Any]:
    stripped_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    markers = [
        line
        for line in stripped_lines
        if (
            "todo" in line.lower()
            or "fixme" in line.lower()
            or "notimplemented" in line.lower()
        )
    ]

    executable_lines = [
        line
        for line in stripped_lines
        if not (
            line.startswith("//")
            or line.startswith("/*")
            or line.startswith("*")
            or line.startswith("#")
        )
    ]

    return {
        "markers": markers[:20],
        "executable_line_count": len(executable_lines),
        "is_probable_placeholder": (
            bool(markers)
            and len(executable_lines) <= 5
        ),
    }


def locate_test_files(
    source_file: Path,
) -> list[str]:
    stem = source_file.stem.lower()

    results: list[str] = []

    for path in REPOSITORY.rglob("*"):
        if not path.is_file():
            continue

        lower_name = path.name.lower()
        lower_path = relative(path).lower()

        if not any(
            token in lower_path
            for token in (
                "test",
                "spec",
                "__tests__",
            )
        ):
            continue

        if (
            stem in lower_name
            or stem.replace("controller", "")
            in lower_name
        ):
            results.append(
                relative(path)
            )

    return results[:30]


def analyze_candidate(
    candidate: dict[str, Any],
) -> dict[str, Any]:
    source_file = (
        REPOSITORY
        / candidate["file"]
    )

    source_text = read_text(
        source_file
    )

    related_files = collect_related_files(
        source_file,
        source_text,
    )

    related_content = "\n\n".join(
        read_text(path)
        for path in related_files
    )

    combined_text = (
        source_text
        + "\n\n"
        + related_content
    )

    rule_key = candidate["rule_key"]

    evidence: list[str] = []
    counter_evidence: list[str] = []
    suggested_test = ""
    status = "needs_runtime_reproduction"
    proof_score = float(
        candidate.get("score", 0)
    )

    if rule_key == "raw_body_to_service":
        forwarding = detect_full_body_forwarding(
            source_text
        )

        guards = detect_validation_guards(
            combined_text
        )

        if forwarding:
            evidence.append(
                "req.body é encaminhado integralmente: "
                + " | ".join(forwarding[:5])
            )
            proof_score += 10

        if guards:
            counter_evidence.append(
                "Possíveis guardas de validação encontradas: "
                + ", ".join(guards)
            )
            proof_score -= 25

        if forwarding and not guards:
            status = "strong_static_evidence"
        elif not forwarding:
            status = "likely_false_positive"

        suggested_test = (
            "Enviar campo extra não documentado no payload e "
            "verificar se ele chega ao serviço ou persistência. "
            "O teste deve usar mocks locais e não chamar serviços externos."
        )

    elif rule_key == "empty_upload_acceptance":
        guards = detect_upload_guards(
            source_text
        )

        uses_file = bool(
            re.search(
                r"\breq\.files?\b",
                source_text,
                re.IGNORECASE,
            )
        )

        if uses_file:
            evidence.append(
                "Controller acessa req.file ou req.files."
            )

        if guards:
            counter_evidence.append(
                "Guarda de upload encontrada: "
                + ", ".join(guards)
            )
            proof_score -= 30
            status = "likely_false_positive"
        elif uses_file:
            evidence.append(
                "Nenhuma guarda explícita foi localizada no controller."
            )
            proof_score += 12
            status = "strong_static_evidence"

        suggested_test = (
            "Invocar o handler com req.file ausente, arquivo de tamanho "
            "zero e lista vazia; confirmar o status HTTP e se ocorre erro."
        )

    elif rule_key == "unsafe_numeric_range":
        cross_guards = detect_cross_field_validation(
            combined_text
        )

        has_min = "budgetMin" in combined_text
        has_max = "budgetMax" in combined_text

        if has_min and has_max:
            evidence.append(
                "Campos mínimo e máximo estão presentes no mesmo fluxo."
            )

        if cross_guards:
            counter_evidence.append(
                "Validação cruzada encontrada: "
                + ", ".join(cross_guards)
            )
            proof_score -= 35
            status = "likely_false_positive"
        elif has_min and has_max:
            evidence.append(
                "Nenhuma validação cruzada foi localizada."
            )
            proof_score += 15
            status = "strong_static_evidence"

        suggested_test = (
            "Validar payload com budgetMin maior que budgetMax e "
            "confirmar se o schema aceita a combinação inválida."
        )

    elif rule_key == "todo_business_logic":
        placeholder = detect_placeholder_file(
            source_text
        )

        if placeholder["markers"]:
            evidence.append(
                "Marcadores encontrados: "
                + " | ".join(
                    placeholder["markers"]
                )
            )

        if placeholder["is_probable_placeholder"]:
            evidence.append(
                "Arquivo possui pouquíssimas linhas executáveis."
            )
            proof_score += 10
            status = "strong_static_evidence"
        else:
            counter_evidence.append(
                "O arquivo contém implementação além do TODO/FIXME."
            )
            proof_score -= 20
            status = "needs_runtime_reproduction"

        suggested_test = (
            "Identificar qual rota ou serviço depende deste arquivo e "
            "executar o fluxo local para confirmar comportamento incompleto."
        )

    else:
        suggested_test = (
            "Criar teste local mínimo para confirmar o comportamento "
            "antes de propor qualquer correção."
        )

    syntax_result = None

    if source_file.suffix.lower() in {
        ".js",
        ".mjs",
        ".cjs",
    }:
        node = shutil.which("node")

        if node:
            syntax_result = run_command(
                [
                    node,
                    "--check",
                    str(source_file),
                ],
                cwd=REPOSITORY,
            )

            if syntax_result["return_code"] != 0:
                evidence.append(
                    "Verificação de sintaxe do Node falhou."
                )
                proof_score += 15
            else:
                counter_evidence.append(
                    "Sintaxe JavaScript válida."
                )
        else:
            counter_evidence.append(
                "Node.js não disponível para verificação de sintaxe."
            )

    tests = locate_test_files(
        source_file
    )

    if tests:
        counter_evidence.append(
            f"{len(tests)} arquivo(s) de teste relacionado(s) encontrado(s)."
        )

    proof_score = round(
        max(
            0,
            min(
                100,
                proof_score,
            ),
        ),
        2,
    )

    if status == "strong_static_evidence":
        if proof_score < 80:
            status = "needs_runtime_reproduction"

    return {
        **candidate,
        "proof_status": status,
        "proof_score": proof_score,
        "evidence": evidence,
        "counter_evidence": counter_evidence,
        "related_files": [
            relative(path)
            for path in related_files
        ],
        "related_tests": tests,
        "suggested_local_test": suggested_test,
        "syntax_result": syntax_result,
        "external_action_performed": False,
        "source_modified": False,
    }


state = json.loads(
    CANDIDATES_STATE.read_text(
        encoding="utf-8"
    )
)

candidates = (
    state.get("top_candidates")
    or []
)

if not candidates:
    raise RuntimeError(
        "Nenhum candidato disponível para o Proof Engine."
    )

PROOF_WORKSPACE.mkdir(
    parents=True,
    exist_ok=True,
)

proofs = [
    analyze_candidate(candidate)
    for candidate in candidates[:20]
]

proofs.sort(
    key=lambda item: (
        {
            "strong_static_evidence": 3,
            "needs_runtime_reproduction": 2,
            "likely_false_positive": 1,
            "blocked_missing_dependencies": 0,
        }.get(
            item["proof_status"],
            0,
        ),
        item["proof_score"],
    ),
    reverse=True,
)

counts: dict[str, int] = {}

for proof in proofs:
    status = proof["proof_status"]

    counts[status] = (
        counts.get(status, 0)
        + 1
    )

proof_state = {
    "generated_at": utc_now(),
    "repository": str(REPOSITORY),
    "commit": state.get("commit"),
    "candidates_analyzed": len(proofs),
    "counts": counts,
    "proofs": proofs,
    "recommended_candidate": (
        proofs[0]
        if proofs
        else None
    ),
    "external_action_performed": False,
    "source_modified": False,
    "issue_created": False,
    "fork_created": False,
    "pull_request_created": False,
}

PROOF_STATE.write_text(
    json.dumps(
        proof_state,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

lines = [
    "# SecureBananaLabs — Local Proof Engine",
    "",
    f"Gerado em: {proof_state['generated_at']}",
    "",
    "## Regra",
    "",
    (
        "Evidência estática forte ainda não representa bug confirmado. "
        "É necessário teste local reproduzível antes de qualquer publicação."
    ),
    "",
    "## Segurança operacional",
    "",
    "- Código-fonte alterado: **não**",
    "- Ação externa realizada: **não**",
    "- Issue criada: **não**",
    "- Fork criado: **não**",
    "- Pull request criado: **não**",
    "",
    "## Resumo",
    "",
    f"- Candidatos analisados: **{len(proofs)}**",
    (
        "- Evidência estática forte: "
        f"**{counts.get('strong_static_evidence', 0)}**"
    ),
    (
        "- Reprodução em runtime necessária: "
        f"**{counts.get('needs_runtime_reproduction', 0)}**"
    ),
    (
        "- Prováveis falsos positivos: "
        f"**{counts.get('likely_false_positive', 0)}**"
    ),
    "",
    "## Ranking de provas",
    "",
]

for index, proof in enumerate(
    proofs,
    1,
):
    lines.extend([
        f"### {index}. {proof['candidate_title']}",
        "",
        f"- Arquivo: `{proof['file']}`",
        f"- Linha aproximada: {proof['line']}",
        f"- Regra: `{proof['rule_key']}`",
        f"- Status: **{proof['proof_status']}**",
        f"- Proof score: **{proof['proof_score']}**",
        "",
        "Evidências:",
        "",
    ])

    if proof["evidence"]:
        lines.extend(
            f"- {item}"
            for item in proof["evidence"]
        )
    else:
        lines.append(
            "- Nenhuma evidência adicional encontrada."
        )

    lines.extend([
        "",
        "Contraevidências:",
        "",
    ])

    if proof["counter_evidence"]:
        lines.extend(
            f"- {item}"
            for item in proof[
                "counter_evidence"
            ]
        )
    else:
        lines.append(
            "- Nenhuma contraevidência encontrada."
        )

    lines.extend([
        "",
        "Teste local sugerido:",
        "",
        f"- {proof['suggested_local_test']}",
        "",
        "Arquivos relacionados:",
        "",
    ])

    if proof["related_files"]:
        lines.extend(
            f"- `{item}`"
            for item in proof["related_files"]
        )
    else:
        lines.append(
            "- Nenhum import local relacionado encontrado."
        )

    lines.extend([
        "",
        "Testes relacionados:",
        "",
    ])

    if proof["related_tests"]:
        lines.extend(
            f"- `{item}`"
            for item in proof["related_tests"]
        )
    else:
        lines.append(
            "- Nenhum teste relacionado identificado."
        )

    lines.append("")

if proofs:
    recommended = proofs[0]

    lines.extend([
        "## Candidato recomendado para reprodução",
        "",
        f"- Hipótese: **{recommended['candidate_title']}**",
        f"- Arquivo: `{recommended['file']}`",
        f"- Status: **{recommended['proof_status']}**",
        f"- Proof score: **{recommended['proof_score']}**",
        f"- Teste sugerido: {recommended['suggested_local_test']}",
        "",
        "## Próximo gate",
        "",
        (
            "Criar um teste isolado no workspace de prova. "
            "O teste precisa falhar no código atual de forma reproduzível. "
            "Nenhuma issue será criada antes disso."
        ),
    ])

REPORT.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print("===== LOCAL PROOF ENGINE =====")
print(
    "Candidates analyzed:",
    len(proofs),
)
print(
    "Strong static evidence:",
    counts.get(
        "strong_static_evidence",
        0,
    ),
)
print(
    "Runtime reproduction required:",
    counts.get(
        "needs_runtime_reproduction",
        0,
    ),
)
print(
    "Likely false positives:",
    counts.get(
        "likely_false_positive",
        0,
    ),
)

print()
print("===== TOP LOCAL PROOF CANDIDATES =====")

for index, proof in enumerate(
    proofs[:15],
    1,
):
    print()
    print(
        f"{index}. {proof['candidate_title']}"
    )
    print(
        "   file:",
        proof["file"],
    )
    print(
        "   status:",
        proof["proof_status"],
    )
    print(
        "   proof score:",
        proof["proof_score"],
    )

    if proof["evidence"]:
        print(
            "   evidence:",
            " | ".join(
                proof["evidence"]
            )[:600],
        )

    if proof["counter_evidence"]:
        print(
            "   counter evidence:",
            " | ".join(
                proof["counter_evidence"]
            )[:600],
        )

    print(
        "   suggested test:",
        proof["suggested_local_test"],
    )

print()
print("===== PROOF ENGINE SAFETY =====")
print("Source code modified: no")
print("External action performed: no")
print("Issue created: no")
print("Fork created: no")
print("Pull request created: no")
print("Report:", REPORT)
