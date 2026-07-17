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
    / "SECUREBANANA_BUSINESS_LOGIC_HUNTER.json"
)

REPORT_FILE = (
    BRAIN
    / "12_REPORTS"
    / "LATEST_SECUREBANANA_BUSINESS_LOGIC_HUNTER.md"
)

EXTENSIONS = {
    ".js",
    ".mjs",
    ".cjs",
    ".ts",
}

STATE_FIELDS = {
    "status",
    "state",
    "stage",
    "approved",
    "accepted",
    "completed",
    "cancelled",
    "canceled",
    "paid",
    "verified",
    "read",
    "active",
    "role",
}

SENSITIVE_VALUES = {
    "approved",
    "accepted",
    "completed",
    "cancelled",
    "canceled",
    "paid",
    "verified",
    "admin",
    "closed",
    "resolved",
    "active",
    "inactive",
    "rejected",
    "withdrawn",
}

MONEY_FIELDS = {
    "amount",
    "price",
    "budget",
    "budgetmin",
    "budgetmax",
    "balance",
    "credit",
    "credits",
    "fee",
    "total",
    "currency",
}

GUARD_PATTERNS = [
    r"\bif\s*\(",
    r"\bswitch\s*\(",
    r"\bthrow\b",
    r"\breturn\s+res\.status\s*\(\s*(?:400|401|403|409|422)",
    r"\bsafeParse\b",
    r"\.parse\s*\(",
    r"\bvalidate\b",
    r"\bassert\b",
]

PREVIOUS_STATE_PATTERNS = [
    r"\.status\s*===",
    r"\.state\s*===",
    r"\.stage\s*===",
    r"\.status\s*!==",
    r"\.state\s*!==",
    r"\.stage\s*!==",
    r"\bincludes\s*\(",
    r"\ballowedTransitions\b",
    r"\btransition\b",
]

AUTH_PATTERNS = [
    r"\breq\.user\b",
    r"\brequest\.user\b",
    r"\bauthenticate\b",
    r"\bauthorize\b",
    r"\brequireAuth\b",
    r"\bpermission\b",
    r"\bforbidden\b",
    r"\b403\b",
]

PERSISTENCE_PATTERNS = [
    r"\.push\s*\(",
    r"\.splice\s*\(",
    r"\.update\s*\(",
    r"\.create\s*\(",
    r"\.save\s*\(",
    r"\.set\s*\(",
    r"\.assign\s*\(",
    r"\bObject\.assign\s*\(",
    r"\.\.\.\s*(?:payload|body|data|input)",
]

PAYMENT_PATTERNS = [
    r"\bpayment\b",
    r"\bstripe\b",
    r"\bamount\b",
    r"\bcurrency\b",
    r"\bbalance\b",
    r"\bcredit\b",
    r"\brefund\b",
    r"\bcharge\b",
    r"\bpayout\b",
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


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def line_number(text: str, position: int) -> int:
    return text.count("\n", 0, position) + 1


def has_pattern(
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


def source_excerpt(
    text: str,
    position: int,
    before: int = 900,
    after: int = 2400,
) -> str:
    start = max(0, position - before)
    end = min(len(text), position + after)

    return compact(
        text[start:end]
    )[:3200]


def discover_assignments(
    text: str,
) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    patterns = [
        re.compile(
            r"\b([A-Za-z_$][A-Za-z0-9_$]*)"
            r"\.(status|state|stage|approved|accepted|completed|"
            r"cancelled|canceled|paid|verified|read|active|role)"
            r"\s*=\s*([^;\r\n]+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\b(status|state|stage|approved|accepted|completed|"
            r"cancelled|canceled|paid|verified|read|active|role)"
            r"\s*:\s*([^,}\r\n]+)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\bObject\.assign\s*\([^,]+,\s*"
            r"(?:payload|body|data|input|req\.body)",
            re.IGNORECASE,
        ),
        re.compile(
            r"\{\s*\.\.\.\s*"
            r"(?:payload|body|data|input|req\.body)",
            re.IGNORECASE,
        ),
    ]

    for pattern in patterns:
        for match in pattern.finditer(text):
            findings.append({
                "position": match.start(),
                "line": line_number(
                    text,
                    match.start(),
                ),
                "match": compact(
                    match.group(0)
                )[:700],
            })

    return findings


def inspect_file(
    path: Path,
) -> list[dict[str, Any]]:
    text = read_text(path)

    if not text:
        return []

    assignments = discover_assignments(text)
    results: list[dict[str, Any]] = []

    for assignment in assignments:
        position = assignment["position"]

        start = max(0, position - 1800)
        end = min(len(text), position + 4200)

        context = text[start:end]

        guards = has_pattern(
            GUARD_PATTERNS,
            context,
        )

        previous_state_check = has_pattern(
            PREVIOUS_STATE_PATTERNS,
            context,
        )

        auth_detected = has_pattern(
            AUTH_PATTERNS,
            context,
        )

        persistence_detected = has_pattern(
            PERSISTENCE_PATTERNS,
            context,
        )

        payment_context = has_pattern(
            PAYMENT_PATTERNS,
            context,
        )

        lowered_match = assignment[
            "match"
        ].lower()

        sensitive_value = any(
            value in lowered_match
            for value in SENSITIVE_VALUES
        )

        money_field = any(
            field in lowered_match
            for field in MONEY_FIELDS
        )

        request_controlled = bool(
            re.search(
                r"\b(?:req\.body|payload|body|data|input)\b",
                context,
                re.IGNORECASE,
            )
        )

        score = 0

        if sensitive_value:
            score += 25

        if request_controlled:
            score += 25

        if persistence_detected:
            score += 20

        if payment_context or money_field:
            score += 20

        if not previous_state_check:
            score += 20

        if not auth_detected:
            score += 10

        if guards:
            score -= 10

        if previous_state_check:
            score -= 35

        score = max(
            0,
            min(100, score),
        )

        if (
            request_controlled
            and persistence_detected
            and not previous_state_check
            and payment_context
        ):
            decision = (
                "HIGH_PRIORITY_FINANCIAL_STATE_REVIEW"
            )

            next_action = (
                "trace_financial_state_transition_and_build_local_test"
            )

        elif (
            request_controlled
            and persistence_detected
            and not previous_state_check
        ):
            decision = (
                "UNGUARDED_STATE_TRANSITION_REVIEW"
            )

            next_action = (
                "trace_transition_and_build_invalid_sequence_test"
            )

        elif (
            sensitive_value
            and not previous_state_check
        ):
            decision = (
                "STATE_MACHINE_REVIEW_REQUIRED"
            )

            next_action = (
                "inspect_call_chain_and_allowed_previous_states"
            )

        elif previous_state_check:
            decision = (
                "PREVIOUS_STATE_CHECK_DETECTED"
            )

            next_action = (
                "inspect_transition_check_quality"
            )

        else:
            decision = (
                "LOW_CONFIDENCE_BUSINESS_LOGIC_SIGNAL"
            )

            next_action = (
                "inspect_related_controller_and_service"
            )

        results.append({
            "file": relative(path),
            "line": assignment["line"],
            "assignment": assignment["match"],
            "request_controlled": request_controlled,
            "persistence_detected": persistence_detected,
            "guard_detected": guards,
            "previous_state_check_detected": (
                previous_state_check
            ),
            "authentication_detected": (
                auth_detected
            ),
            "payment_context_detected": (
                payment_context
            ),
            "sensitive_value_detected": (
                sensitive_value
            ),
            "risk_score": score,
            "decision": decision,
            "recommended_next_action": (
                next_action
            ),
            "excerpt": source_excerpt(
                text,
                position,
            ),
        })

    return results


source_files = sorted(
    path
    for path in SOURCE_ROOT.rglob("*")
    if (
        path.is_file()
        and path.suffix.lower()
        in EXTENSIONS
    )
)

findings: list[dict[str, Any]] = []

for source_file in source_files:
    findings.extend(
        inspect_file(source_file)
    )

priority = {
    "HIGH_PRIORITY_FINANCIAL_STATE_REVIEW": 5,
    "UNGUARDED_STATE_TRANSITION_REVIEW": 4,
    "STATE_MACHINE_REVIEW_REQUIRED": 3,
    "PREVIOUS_STATE_CHECK_DETECTED": 2,
    "LOW_CONFIDENCE_BUSINESS_LOGIC_SIGNAL": 1,
}

findings.sort(
    key=lambda item: (
        priority.get(
            item["decision"],
            0,
        ),
        item["risk_score"],
        item["payment_context_detected"],
    ),
    reverse=True,
)

financial_candidates = [
    item
    for item in findings
    if item["decision"]
    == "HIGH_PRIORITY_FINANCIAL_STATE_REVIEW"
]

unguarded_candidates = [
    item
    for item in findings
    if item["decision"]
    == "UNGUARDED_STATE_TRANSITION_REVIEW"
]

state_candidates = [
    item
    for item in findings
    if item["decision"]
    == "STATE_MACHINE_REVIEW_REQUIRED"
]

recommended = (
    financial_candidates[0]
    if financial_candidates
    else (
        unguarded_candidates[0]
        if unguarded_candidates
        else (
            state_candidates[0]
            if state_candidates
            else (
                findings[0]
                if findings
                else None
            )
        )
    )
)

if financial_candidates:
    overall_decision = (
        "FINANCIAL_STATE_CANDIDATE_FOUND"
    )

    next_action = (
        "trace_highest_priority_financial_transition"
    )

elif unguarded_candidates:
    overall_decision = (
        "UNGUARDED_STATE_CANDIDATE_FOUND"
    )

    next_action = (
        "trace_highest_priority_state_transition"
    )

elif state_candidates:
    overall_decision = (
        "STATE_MACHINE_CANDIDATE_FOUND"
    )

    next_action = (
        "inspect_highest_priority_state_candidate"
    )

elif findings:
    overall_decision = (
        "BUSINESS_LOGIC_SIGNALS_INCONCLUSIVE"
    )

    next_action = (
        "inspect_top_signal_manually"
    )

else:
    overall_decision = (
        "NO_STATE_TRANSITION_SIGNAL_FOUND"
    )

    next_action = (
        "move_to_duplicate_request_and_race_condition_analysis"
    )

state = {
    "generated_at": utc_now(),
    "repository": str(REPOSITORY),
    "source_files_scanned": len(
        source_files
    ),
    "findings_total": len(findings),
    "financial_candidates": len(
        financial_candidates
    ),
    "unguarded_state_candidates": len(
        unguarded_candidates
    ),
    "state_machine_candidates": len(
        state_candidates
    ),
    "overall_decision": overall_decision,
    "recommended_candidate": recommended,
    "recommended_next_action": (
        next_action
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

lines = [
    (
        "# SecureBananaLabs — "
        "Business Logic Hunter"
    ),
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
        "- Achados: "
        f"**{len(findings)}**"
    ),
    (
        "- Candidatos financeiros: "
        f"**{len(financial_candidates)}**"
    ),
    (
        "- Transições sem guarda: "
        f"**{len(unguarded_candidates)}**"
    ),
    (
        "- Candidatos de state machine: "
        f"**{len(state_candidates)}**"
    ),
    (
        "- Próxima ação: "
        f"**{next_action}**"
    ),
    "",
]

if recommended:
    lines.extend([
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
            "- Assignment: "
            f"`{recommended['assignment']}`"
        ),
        (
            "- Controlado pela requisição: "
            f"**{recommended['request_controlled']}**"
        ),
        (
            "- Persistência detectada: "
            f"**{recommended['persistence_detected']}**"
        ),
        (
            "- Estado anterior verificado: "
            f"**{recommended['previous_state_check_detected']}**"
        ),
        (
            "- Contexto financeiro: "
            f"**{recommended['payment_context_detected']}**"
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

lines.extend([
    "## Ranking",
    "",
])

for index, finding in enumerate(
    findings[:50],
    1,
):
    lines.extend([
        (
            f"### {index}. "
            f"{finding['file']}:"
            f"{finding['line']}"
        ),
        "",
        (
            "- Assignment: "
            f"`{finding['assignment']}`"
        ),
        (
            "- Controlado pela requisição: "
            f"**{finding['request_controlled']}**"
        ),
        (
            "- Persistência: "
            f"**{finding['persistence_detected']}**"
        ),
        (
            "- Estado anterior verificado: "
            f"**{finding['previous_state_check_detected']}**"
        ),
        (
            "- Contexto financeiro: "
            f"**{finding['payment_context_detected']}**"
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

lines.extend([
    "## Limitação",
    "",
    (
        "Os resultados são candidatos estáticos. "
        "Nenhuma vulnerabilidade é considerada confirmada "
        "sem reprodução local do fluxo completo."
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
]

REPORT_FILE.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print(
    "===== BUSINESS LOGIC HUNTER ====="
)
print(
    "Source files scanned:",
    len(source_files),
)
print(
    "Findings total:",
    len(findings),
)
print(
    "Financial candidates:",
    len(financial_candidates),
)
print(
    "Unguarded state candidates:",
    len(unguarded_candidates),
)
print(
    "State-machine candidates:",
    len(state_candidates),
)
print(
    "Overall decision:",
    overall_decision,
)
print(
    "Recommended next action:",
    next_action,
)

if recommended:
    print()
    print(
        "===== RECOMMENDED BUSINESS LOGIC CANDIDATE ====="
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
        "Assignment:",
        recommended["assignment"],
    )
    print(
        "Request controlled:",
        recommended["request_controlled"],
    )
    print(
        "Persistence detected:",
        recommended["persistence_detected"],
    )
    print(
        "Previous-state check detected:",
        recommended[
            "previous_state_check_detected"
        ],
    )
    print(
        "Authentication detected:",
        recommended[
            "authentication_detected"
        ],
    )
    print(
        "Payment context detected:",
        recommended[
            "payment_context_detected"
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
        "===== RECOMMENDED BUSINESS LOGIC EXCERPT ====="
    )
    print(
        recommended["excerpt"]
    )

print()
print(
    "===== TOP BUSINESS LOGIC CANDIDATES ====="
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
        "   Assignment:",
        finding["assignment"],
    )
    print(
        "   Request controlled:",
        finding["request_controlled"],
    )
    print(
        "   Persistence:",
        finding["persistence_detected"],
    )
    print(
        "   Previous-state check:",
        finding[
            "previous_state_check_detected"
        ],
    )
    print(
        "   Payment context:",
        finding[
            "payment_context_detected"
        ],
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
    "===== BUSINESS LOGIC HUNTER SAFETY ====="
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
