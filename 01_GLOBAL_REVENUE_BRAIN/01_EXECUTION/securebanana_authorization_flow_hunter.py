from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HOME = Path.home()

BRAIN = (
    HOME
    / "AI-Network-Lab-Brain"
    / "01_GLOBAL_REVENUE_BRAIN"
)

REPOSITORY = (
    HOME
    / "Revenue-Workspaces"
    / "SecureBananaLabs-bug-bounty-743"
    / "repository"
)

SOURCE_ROOT = (
    REPOSITORY
    / "apps"
    / "api"
    / "src"
)

STATE_FILE = (
    BRAIN
    / "00_CURRENT_STATE"
    / "SECUREBANANA_AUTHORIZATION_FLOW_HUNTER.json"
)

REPORT_FILE = (
    BRAIN
    / "12_REPORTS"
    / "LATEST_SECUREBANANA_AUTHORIZATION_FLOW_HUNTER.md"
)

SUPPORTED_EXTENSIONS = {
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
}

REQUEST_ID_PATTERNS = [
    (
        "params",
        re.compile(
            r"\breq\.params\.([A-Za-z_$][A-Za-z0-9_$]*)",
            re.IGNORECASE,
        ),
    ),
    (
        "query",
        re.compile(
            r"\breq\.query\.([A-Za-z_$][A-Za-z0-9_$]*)",
            re.IGNORECASE,
        ),
    ),
    (
        "body",
        re.compile(
            r"\breq\.body\.([A-Za-z_$][A-Za-z0-9_$]*)",
            re.IGNORECASE,
        ),
    ),
]

DATA_ACCESS_PATTERNS = [
    r"\.findById\s*\(",
    r"\.findUnique\s*\(",
    r"\.findFirst\s*\(",
    r"\.findOne\s*\(",
    r"\.getById\s*\(",
    r"\.find\s*\(",
    r"\.filter\s*\(",
]

MUTATION_PATTERNS = [
    r"\.update\s*\(",
    r"\.delete\s*\(",
    r"\.remove\s*\(",
    r"\.destroy\s*\(",
    r"\.splice\s*\(",
    r"\.push\s*\(",
]

AUTH_PATTERNS = [
    r"\breq\.user\b",
    r"\brequest\.user\b",
    r"\bauthMiddleware\b",
    r"\bauthenticate\b",
    r"\brequireAuth\b",
    r"\bverifyToken\b",
    r"\bauthorize\b",
    r"\bprotect\b",
]

OWNERSHIP_PATTERNS = [
    r"\bownerId\b",
    r"\bcreatedBy\b",
    r"\bsenderId\b",
    r"\breviewerId\b",
    r"\buserId\s*===",
    r"\bownerId\s*===",
    r"\bcreatedBy\s*===",
    r"\bisOwner\b",
    r"\bownership\b",
    r"\bpermission\b",
    r"\bforbidden\b",
    r"\b403\b",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return ""


def relative(path: Path) -> str:
    try:
        return str(
            path.relative_to(REPOSITORY)
        ).replace("\\", "/")
    except ValueError:
        return str(path)


def line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def compact(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def excerpt(
    text: str,
    position: int,
    before: int = 700,
    after: int = 1800,
) -> str:
    start = max(0, position - before)
    end = min(len(text), position + after)

    return compact(
        text[start:end]
    )[:2400]


def pattern_found(
    patterns: list[str],
    text: str,
) -> bool:
    return any(
        re.search(
            pattern,
            text,
            re.IGNORECASE | re.DOTALL,
        )
        for pattern in patterns
    )


def identifier_like(name: str) -> bool:
    lowered = name.lower()

    return (
        lowered == "id"
        or lowered.endswith("id")
        or lowered.endswith("_id")
    )


def inspect_file(path: Path) -> list[dict[str, Any]]:
    text = read_text(path)

    if not text:
        return []

    findings: list[dict[str, Any]] = []

    for source_type, request_pattern in REQUEST_ID_PATTERNS:
        for match in request_pattern.finditer(text):
            identifier = match.group(1)

            if not identifier_like(identifier):
                continue

            position = match.start()

            context_start = max(0, position - 1200)
            context_end = min(
                len(text),
                position + 3500,
            )

            context = text[
                context_start:context_end
            ]

            data_access = pattern_found(
                DATA_ACCESS_PATTERNS,
                context,
            )

            mutation = pattern_found(
                MUTATION_PATTERNS,
                context,
            )

            auth_detected = pattern_found(
                AUTH_PATTERNS,
                context,
            )

            ownership_check = pattern_found(
                OWNERSHIP_PATTERNS,
                context,
            )

            identifier_after_input = context[
                max(
                    0,
                    position - context_start,
                ):
            ]

            identifier_reused = bool(
                re.search(
                    rf"\b{re.escape(identifier)}\b",
                    identifier_after_input,
                    re.IGNORECASE,
                )
            )

            risk_score = 0

            if source_type == "params":
                risk_score += 25
            elif source_type == "query":
                risk_score += 20
            else:
                risk_score += 15

            if data_access:
                risk_score += 25

            if mutation:
                risk_score += 25

            if identifier_reused:
                risk_score += 10

            if auth_detected:
                risk_score -= 10

            if ownership_check:
                risk_score -= 35

            risk_score = max(
                0,
                min(100, risk_score),
            )

            if mutation and not ownership_check:
                decision = (
                    "HIGH_PRIORITY_AUTHORIZATION_REVIEW"
                )

                next_action = (
                    "trace_mutation_route_and_build_cross_user_test"
                )

            elif data_access and not ownership_check:
                decision = (
                    "AUTHORIZATION_READ_REVIEW"
                )

                next_action = (
                    "trace_read_route_and_build_cross_user_test"
                )

            elif ownership_check:
                decision = (
                    "OWNERSHIP_CHECK_DETECTED"
                )

                next_action = (
                    "inspect_ownership_check_quality"
                )

            else:
                decision = (
                    "INSUFFICIENT_FLOW_EVIDENCE"
                )

                next_action = (
                    "trace_service_and_model"
                )

            findings.append({
                "file": relative(path),
                "line": line_number(
                    text,
                    position,
                ),
                "identifier": identifier,
                "identifier_source": source_type,
                "data_access_detected": data_access,
                "mutation_detected": mutation,
                "auth_detected": auth_detected,
                "ownership_check_detected": (
                    ownership_check
                ),
                "identifier_reused": (
                    identifier_reused
                ),
                "risk_score": risk_score,
                "decision": decision,
                "recommended_next_action": (
                    next_action
                ),
                "excerpt": excerpt(
                    text,
                    position,
                ),
            })

    return findings


source_files = sorted(
    path
    for path in SOURCE_ROOT.rglob("*")
    if (
        path.is_file()
        and path.suffix.lower()
        in SUPPORTED_EXTENSIONS
    )
)

findings: list[dict[str, Any]] = []

for path in source_files:
    findings.extend(
        inspect_file(path)
    )

priority = {
    "HIGH_PRIORITY_AUTHORIZATION_REVIEW": 4,
    "AUTHORIZATION_READ_REVIEW": 3,
    "OWNERSHIP_CHECK_DETECTED": 2,
    "INSUFFICIENT_FLOW_EVIDENCE": 1,
}

findings.sort(
    key=lambda item: (
        priority.get(
            item["decision"],
            0,
        ),
        item["risk_score"],
        item["mutation_detected"],
    ),
    reverse=True,
)

high_priority = [
    item
    for item in findings
    if item["decision"]
    == "HIGH_PRIORITY_AUTHORIZATION_REVIEW"
]

read_candidates = [
    item
    for item in findings
    if item["decision"]
    == "AUTHORIZATION_READ_REVIEW"
]

recommended = (
    high_priority[0]
    if high_priority
    else (
        read_candidates[0]
        if read_candidates
        else (
            findings[0]
            if findings
            else None
        )
    )
)

if high_priority:
    overall_decision = (
        "AUTHORIZATION_MUTATION_CANDIDATE_FOUND"
    )

    recommended_next_action = (
        "trace_highest_priority_mutation_candidate"
    )

elif read_candidates:
    overall_decision = (
        "AUTHORIZATION_READ_CANDIDATE_FOUND"
    )

    recommended_next_action = (
        "trace_highest_priority_read_candidate"
    )

elif findings:
    overall_decision = (
        "AUTHORIZATION_EVIDENCE_INCONCLUSIVE"
    )

    recommended_next_action = (
        "inspect_top_candidate_dependencies"
    )

else:
    overall_decision = (
        "NO_IDENTIFIER_BASED_FLOW_FOUND"
    )

    recommended_next_action = (
        "move_to_business_logic_analysis"
    )

state = {
    "generated_at": utc_now(),
    "repository": str(REPOSITORY),
    "source_files_scanned": len(source_files),
    "findings_total": len(findings),
    "high_priority_mutation_candidates": len(
        high_priority
    ),
    "read_authorization_candidates": len(
        read_candidates
    ),
    "overall_decision": overall_decision,
    "recommended_candidate": recommended,
    "recommended_next_action": (
        recommended_next_action
    ),
    "findings": findings,
    "source_modified": False,
    "dependency_install_performed": False,
    "runtime_request_performed": False,
    "external_publication_performed": False,
    "issue_created": False,
    "comment_created": False,
    "fork_created": False,
    "pull_request_created": False,
}

STATE_FILE.write_text(
    json.dumps(
        state,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

report_lines = [
    "# SecureBananaLabs — Authorization Flow Hunter",
    "",
    f"Gerado em: {state['generated_at']}",
    "",
    "## Resultado",
    "",
    f"- Decisão: **{overall_decision}**",
    (
        "- Arquivos analisados: "
        f"**{len(source_files)}**"
    ),
    (
        "- Achados totais: "
        f"**{len(findings)}**"
    ),
    (
        "- Candidatos de mutação: "
        f"**{len(high_priority)}**"
    ),
    (
        "- Candidatos de leitura: "
        f"**{len(read_candidates)}**"
    ),
    (
        "- Próxima ação: "
        f"**{recommended_next_action}**"
    ),
    "",
]

if recommended:
    report_lines.extend([
        "## Candidato recomendado",
        "",
        (
            "- Arquivo: "
            f"`{recommended['file']}`"
        ),
        (
            "- Linha: "
            f"**{recommended['line']}**"
        ),
        (
            "- Identificador: "
            f"`{recommended['identifier']}`"
        ),
        (
            "- Origem: "
            f"**{recommended['identifier_source']}**"
        ),
        (
            "- Mutação: "
            f"**{recommended['mutation_detected']}**"
        ),
        (
            "- Acesso a dados: "
            f"**{recommended['data_access_detected']}**"
        ),
        (
            "- Autenticação detectada: "
            f"**{recommended['auth_detected']}**"
        ),
        (
            "- Ownership check: "
            f"**{recommended['ownership_check_detected']}**"
        ),
        (
            "- Risk score: "
            f"**{recommended['risk_score']}**"
        ),
        (
            "- Decisão: "
            f"**{recommended['decision']}**"
        ),
        "",
        "```javascript",
        recommended["excerpt"],
        "```",
        "",
    ])

report_lines.extend([
    "## Ranking",
    "",
])

for index, finding in enumerate(
    findings[:50],
    1,
):
    report_lines.extend([
        (
            f"### {index}. "
            f"{finding['file']}:"
            f"{finding['line']}"
        ),
        "",
        (
            "- Identificador: "
            f"`{finding['identifier']}`"
        ),
        (
            "- Origem: "
            f"**{finding['identifier_source']}**"
        ),
        (
            "- Mutação: "
            f"**{finding['mutation_detected']}**"
        ),
        (
            "- Acesso a dados: "
            f"**{finding['data_access_detected']}**"
        ),
        (
            "- Auth detectado: "
            f"**{finding['auth_detected']}**"
        ),
        (
            "- Ownership check: "
            f"**{finding['ownership_check_detected']}**"
        ),
        (
            "- Risk score: "
            f"**{finding['risk_score']}**"
        ),
        (
            "- Decisão: "
            f"**{finding['decision']}**"
        ),
        "",
    ])

report_lines.extend([
    "## Limitação",
    "",
    (
        "A ausência de uma checagem no contexto local "
        "não comprova uma vulnerabilidade. A autorização "
        "pode existir em outra camada."
    ),
    "",
    "## Segurança operacional",
    "",
    "- Código original alterado: **não**",
    "- Dependências instaladas: **não**",
    "- Requisição de runtime: **não**",
    "- Publicação externa: **não**",
    "- Issue criada: **não**",
    "- Comentário criado: **não**",
    "- Fork criado: **não**",
    "- Pull request criado: **não**",
])

REPORT_FILE.write_text(
    "\n".join(report_lines),
    encoding="utf-8",
)

print()
print("===== AUTHORIZATION FLOW HUNTER =====")
print(
    "Source files scanned:",
    len(source_files),
)
print(
    "Findings total:",
    len(findings),
)
print(
    "High-priority mutation candidates:",
    len(high_priority),
)
print(
    "Read authorization candidates:",
    len(read_candidates),
)
print(
    "Overall decision:",
    overall_decision,
)
print(
    "Recommended next action:",
    recommended_next_action,
)

if recommended:
    print()
    print(
        "===== RECOMMENDED AUTHORIZATION CANDIDATE ====="
    )
    print(
        "File:",
        recommended["file"],
    )
    print(
        "Line:",
        recommended["line"],
    )
    print(
        "Identifier:",
        recommended["identifier"],
    )
    print(
        "Identifier source:",
        recommended["identifier_source"],
    )
    print(
        "Data access detected:",
        recommended["data_access_detected"],
    )
    print(
        "Mutation detected:",
        recommended["mutation_detected"],
    )
    print(
        "Auth detected:",
        recommended["auth_detected"],
    )
    print(
        "Ownership check detected:",
        recommended[
            "ownership_check_detected"
        ],
    )
    print(
        "Risk score:",
        recommended["risk_score"],
    )
    print(
        "Decision:",
        recommended["decision"],
    )
    print(
        "Recommended next action:",
        recommended[
            "recommended_next_action"
        ],
    )
    print()
    print(
        "===== RECOMMENDED AUTHORIZATION EXCERPT ====="
    )
    print(
        recommended["excerpt"]
    )

print()
print(
    "===== TOP AUTHORIZATION CANDIDATES ====="
)

for index, finding in enumerate(
    findings[:15],
    1,
):
    print()
    print(
        f"{index}. "
        f"{finding['file']}:"
        f"{finding['line']}"
    )
    print(
        "   Identifier:",
        finding["identifier"],
    )
    print(
        "   Source:",
        finding["identifier_source"],
    )
    print(
        "   Mutation:",
        finding["mutation_detected"],
    )
    print(
        "   Data access:",
        finding["data_access_detected"],
    )
    print(
        "   Auth:",
        finding["auth_detected"],
    )
    print(
        "   Ownership check:",
        finding["ownership_check_detected"],
    )
    print(
        "   Risk score:",
        finding["risk_score"],
    )
    print(
        "   Decision:",
        finding["decision"],
    )

print()
print(
    "===== AUTHORIZATION FLOW HUNTER SAFETY ====="
)
print("Original source modified: no")
print("Dependency install performed: no")
print("Runtime request performed: no")
print("External publication performed: no")
print("Issue created: no")
print("Comment created: no")
print("Fork created: no")
print("Pull request created: no")
print("Report:", REPORT_FILE)
