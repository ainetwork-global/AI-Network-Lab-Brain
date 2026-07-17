from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


BRAIN_ROOT = (
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

STATE_FILE = (
    BRAIN_ROOT
    / "00_CURRENT_STATE"
    / "SECUREBANANA_REMAINING_BODY_FLOWS.json"
)

REPORT_FILE = (
    BRAIN_ROOT
    / "12_REPORTS"
    / "LATEST_SECUREBANANA_REMAINING_BODY_FLOWS.md"
)

FLOWS = [
    {
        "key": "message",
        "controller": (
            "apps/api/src/controllers/"
            "messageController.js"
        ),
        "service": (
            "apps/api/src/services/"
            "messageService.js"
        ),
        "function": "sendMessage",
    },
    {
        "key": "notification",
        "controller": (
            "apps/api/src/controllers/"
            "notificationController.js"
        ),
        "service": (
            "apps/api/src/services/"
            "notificationService.js"
        ),
        "function": "createNotification",
    },
    {
        "key": "proposal",
        "controller": (
            "apps/api/src/controllers/"
            "proposalController.js"
        ),
        "service": (
            "apps/api/src/services/"
            "proposalService.js"
        ),
        "function": "createProposal",
    },
    {
        "key": "review",
        "controller": (
            "apps/api/src/controllers/"
            "reviewController.js"
        ),
        "service": (
            "apps/api/src/services/"
            "reviewService.js"
        ),
        "function": "createReview",
    },
    {
        "key": "user",
        "controller": (
            "apps/api/src/controllers/"
            "userController.js"
        ),
        "service": (
            "apps/api/src/services/"
            "userService.js"
        ),
        "function": "createUser",
    },
]


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def read_text(path: Path) -> str:
    try:
        return path.read_text(
            encoding="utf-8",
            errors="ignore",
        )
    except OSError:
        return ""


def compact_match(
    pattern: str,
    text: str,
) -> list[str]:
    matches: list[str] = []

    for match in re.finditer(
        pattern,
        text,
        re.IGNORECASE | re.DOTALL,
    ):
        value = re.sub(
            r"\s+",
            " ",
            match.group(0),
        ).strip()

        matches.append(
            value[:500]
        )

    return matches[:20]


def inspect_flow(
    flow: dict[str, str],
) -> dict[str, Any]:
    controller_path = (
        REPOSITORY
        / flow["controller"]
    )

    service_path = (
        REPOSITORY
        / flow["service"]
    )

    controller_exists = (
        controller_path.exists()
    )

    service_exists = (
        service_path.exists()
    )

    controller_text = read_text(
        controller_path
    )

    service_text = read_text(
        service_path
    )

    combined = (
        controller_text
        + "\n\n"
        + service_text
    )

    body_forwarded = bool(
        re.search(
            rf"\b{re.escape(flow['function'])}"
            r"\s*\(\s*req\.body\s*\)",
            controller_text,
            re.IGNORECASE,
        )
    )

    destructuring_matches = compact_match(
        (
            r"(?:const|let|var)\s*"
            r"\{[^}]{1,800}\}\s*="
            r"\s*(?:payload|data|body|input)"
        ),
        service_text,
    )

    property_accesses = sorted(
        set(
            re.findall(
                (
                    r"\b(?:payload|data|body|input)"
                    r"\.([A-Za-z_$][A-Za-z0-9_$]*)"
                ),
                service_text,
            )
        )
    )

    optional_property_accesses = sorted(
        set(
            re.findall(
                (
                    r"\b(?:payload|data|body|input)"
                    r"\?\."
                    r"([A-Za-z_$][A-Za-z0-9_$]*)"
                ),
                service_text,
            )
        )
    )

    selected_fields = sorted(
        set(
            property_accesses
            + optional_property_accesses
        )
    )

    spread_matches = compact_match(
        (
            r"\.\.\.\s*"
            r"(?:payload|data|body|input)"
        ),
        service_text,
    )

    direct_data_pass_matches = compact_match(
        (
            r"\bdata\s*:\s*"
            r"(?:payload|data|body|input)"
            r"\b"
        ),
        service_text,
    )

    direct_argument_matches = compact_match(
        (
            r"\.\s*(?:create|update|insert|save)"
            r"\s*\(\s*"
            r"(?:payload|data|body|input)"
            r"\s*\)"
        ),
        service_text,
    )

    prisma_matches = compact_match(
        (
            r"\bprisma\."
            r"[A-Za-z_$][A-Za-z0-9_$]*"
            r"\.(?:create|update|upsert)"
            r"\s*\([^;]{1,1500}\)"
        ),
        service_text,
    )

    validation_matches = compact_match(
        (
            r"(?:safeParse|schema\.parse|"
            r"validationResult|matchedData|"
            r"\.validate|sanitize|whitelist|"
            r"allowedFields)"
        ),
        combined,
    )

    todo_matches = compact_match(
        r"(?:TODO|FIXME)[^\r\n]*",
        combined,
    )

    return_literal_matches = compact_match(
        r"return\s*\{[^;]{1,1500}\}",
        service_text,
    )

    throws_not_implemented = bool(
        re.search(
            (
                r"throw\s+new\s+Error\s*\("
                r"[^)]*(?:not implemented|todo)"
            ),
            service_text,
            re.IGNORECASE,
        )
    )

    placeholder = bool(
        todo_matches
        and (
            len(
                [
                    line
                    for line in service_text.splitlines()
                    if line.strip()
                    and not line.strip().startswith(
                        ("//", "/*", "*")
                    )
                ]
            )
            <= 12
        )
    )

    unrestricted_persistence = bool(
        spread_matches
        or direct_data_pass_matches
        or direct_argument_matches
    )

    explicit_field_selection = bool(
        destructuring_matches
        or selected_fields
    )

    score = 25 if body_forwarded else 0

    if unrestricted_persistence:
        score += 55

    if prisma_matches:
        score += 10

    if validation_matches:
        score -= 35

    if explicit_field_selection:
        score -= 35

    if placeholder:
        score -= 20

    if throws_not_implemented:
        score -= 30

    score = round(
        max(
            0,
            min(
                100,
                score,
            ),
        ),
        2,
    )

    if not service_exists:
        decision = (
            "BLOCKED_SERVICE_NOT_FOUND"
        )

        next_action = (
            "locate_actual_service_import"
        )

    elif unrestricted_persistence:
        decision = (
            "BUILD_TARGETED_RUNTIME_PROOF"
        )

        next_action = (
            "mock_persistence_and_test_extra_field"
        )

    elif validation_matches:
        decision = (
            "LIKELY_FALSE_POSITIVE_VALIDATED"
        )

        next_action = (
            "discard_candidate"
        )

    elif explicit_field_selection:
        decision = (
            "LIKELY_FALSE_POSITIVE_FIELD_SELECTION"
        )

        next_action = (
            "discard_candidate"
        )

    elif placeholder:
        decision = (
            "PLACEHOLDER_IMPLEMENTATION"
        )

        next_action = (
            "do_not_treat_body_forwarding_as_bug"
        )

    else:
        decision = (
            "DEEPER_FLOW_INSPECTION_REQUIRED"
        )

        next_action = (
            "inspect_routes_models_and_dependencies"
        )

    return {
        "flow": flow["key"],
        "function": flow["function"],
        "controller": flow["controller"],
        "service": flow["service"],
        "controller_exists": controller_exists,
        "service_exists": service_exists,
        "body_forwarded": body_forwarded,
        "explicit_field_selection": (
            explicit_field_selection
        ),
        "selected_fields": selected_fields,
        "destructuring_matches": (
            destructuring_matches
        ),
        "spread_matches": spread_matches,
        "direct_data_pass_matches": (
            direct_data_pass_matches
        ),
        "direct_argument_matches": (
            direct_argument_matches
        ),
        "prisma_matches": prisma_matches,
        "validation_matches": (
            validation_matches
        ),
        "todo_matches": todo_matches,
        "return_literal_matches": (
            return_literal_matches
        ),
        "placeholder": placeholder,
        "throws_not_implemented": (
            throws_not_implemented
        ),
        "unrestricted_persistence": (
            unrestricted_persistence
        ),
        "risk_score": score,
        "decision": decision,
        "recommended_next_action": (
            next_action
        ),
        "controller_source": (
            controller_text
        ),
        "service_source": service_text,
        "source_modified": False,
        "external_action_performed": False,
    }


results = [
    inspect_flow(flow)
    for flow in FLOWS
]

decision_priority = {
    "BUILD_TARGETED_RUNTIME_PROOF": 5,
    "DEEPER_FLOW_INSPECTION_REQUIRED": 4,
    "BLOCKED_SERVICE_NOT_FOUND": 3,
    "PLACEHOLDER_IMPLEMENTATION": 2,
    "LIKELY_FALSE_POSITIVE_VALIDATED": 1,
    "LIKELY_FALSE_POSITIVE_FIELD_SELECTION": 1,
}

results.sort(
    key=lambda item: (
        decision_priority.get(
            item["decision"],
            0,
        ),
        item["risk_score"],
    ),
    reverse=True,
)

recommended = (
    results[0]
    if results
    else None
)

state = {
    "generated_at": utc_now(),
    "repository": str(REPOSITORY),
    "flows_analyzed": len(results),
    "results": results,
    "recommended_candidate": recommended,
    "discarded_candidates": [
        {
            "flow": "payment",
            "reason": (
                "service selects amount and currency; "
                "placeholder Stripe implementation"
            ),
        },
        {
            "flow": "job_budget",
            "reason": (
                "runtime confirmed but duplicate "
                "candidate already identified"
            ),
        },
        {
            "flow": "upload",
            "reason": (
                "duplicate candidate already identified"
            ),
        },
    ],
    "source_modified": False,
    "dependency_install_performed": False,
    "external_action_performed": False,
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
    "# SecureBananaLabs — Remaining Body Flows",
    "",
    f"Gerado em: {state['generated_at']}",
    "",
    "## Objetivo",
    "",
    (
        "Determinar se o encaminhamento integral de "
        "`req.body` resulta em persistência irrestrita "
        "ou se os serviços selecionam campos explicitamente."
    ),
    "",
    "## Ranking",
    "",
]

for index, result in enumerate(
    results,
    1,
):
    lines.extend([
        f"### {index}. {result['flow']}",
        "",
        f"- Função: `{result['function']}`",
        f"- Controller: `{result['controller']}`",
        f"- Service: `{result['service']}`",
        (
            "- `req.body` encaminhado: "
            f"**{result['body_forwarded']}**"
        ),
        (
            "- Seleção explícita de campos: "
            f"**{result['explicit_field_selection']}**"
        ),
        (
            "- Campos usados: "
            f"`{', '.join(result['selected_fields'])}`"
        ),
        (
            "- Persistência irrestrita: "
            f"**{result['unrestricted_persistence']}**"
        ),
        (
            "- Placeholder: "
            f"**{result['placeholder']}**"
        ),
        (
            "- Risk score: "
            f"**{result['risk_score']}**"
        ),
        (
            "- Decisão: "
            f"**{result['decision']}**"
        ),
        (
            "- Próxima ação: "
            f"**{result['recommended_next_action']}**"
        ),
        "",
        "#### Service source",
        "",
        "```javascript",
        result["service_source"],
        "```",
        "",
    ])

if recommended:
    lines.extend([
        "## Candidato recomendado",
        "",
        f"- Fluxo: **{recommended['flow']}**",
        (
            "- Decisão: "
            f"**{recommended['decision']}**"
        ),
        (
            "- Risk score: "
            f"**{recommended['risk_score']}**"
        ),
        (
            "- Próxima ação: "
            f"**{recommended['recommended_next_action']}**"
        ),
        "",
    ])

lines.extend([
    "## Segurança operacional",
    "",
    "- Código original alterado: **não**",
    "- Dependências instaladas: **não**",
    "- Ação externa realizada: **não**",
    "- Issue criada: **não**",
    "- Comentário criado: **não**",
    "- Fork criado: **não**",
    "- Pull request criado: **não**",
])

REPORT_FILE.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print(
    "===== REMAINING BODY FLOWS ====="
)

for index, result in enumerate(
    results,
    1,
):
    print()
    print(
        f"{index}. {result['flow']}"
    )
    print(
        "   body forwarded:",
        result["body_forwarded"],
    )
    print(
        "   explicit field selection:",
        result["explicit_field_selection"],
    )
    print(
        "   selected fields:",
        (
            ", ".join(
                result["selected_fields"]
            )
            or "none"
        ),
    )
    print(
        "   unrestricted persistence:",
        result["unrestricted_persistence"],
    )
    print(
        "   placeholder:",
        result["placeholder"],
    )
    print(
        "   risk score:",
        result["risk_score"],
    )
    print(
        "   decision:",
        result["decision"],
    )
    print(
        "   recommended next action:",
        result["recommended_next_action"],
    )

    if result["spread_matches"]:
        print(
            "   spread evidence:",
            " | ".join(
                result["spread_matches"]
            ),
        )

    if result["direct_data_pass_matches"]:
        print(
            "   direct data evidence:",
            " | ".join(
                result[
                    "direct_data_pass_matches"
                ]
            ),
        )

    if result["validation_matches"]:
        print(
            "   validation evidence:",
            " | ".join(
                result["validation_matches"]
            ),
        )

if recommended:
    print()
    print(
        "===== RECOMMENDED BODY FLOW ====="
    )
    print(
        "Flow:",
        recommended["flow"],
    )
    print(
        "Service:",
        recommended["service"],
    )
    print(
        "Decision:",
        recommended["decision"],
    )
    print(
        "Risk score:",
        recommended["risk_score"],
    )
    print(
        "Recommended next action:",
        recommended[
            "recommended_next_action"
        ],
    )
    print()
    print(
        "===== RECOMMENDED SERVICE SOURCE ====="
    )
    print(
        recommended["service_source"]
    )

print()
print(
    "===== REMAINING BODY FLOWS SAFETY ====="
)
print("Original source modified: no")
print("Dependency install performed: no")
print("External action performed: no")
print("Issue created: no")
print("Comment created: no")
print("Fork created: no")
print("Pull request created: no")
print("Report:", REPORT_FILE)
