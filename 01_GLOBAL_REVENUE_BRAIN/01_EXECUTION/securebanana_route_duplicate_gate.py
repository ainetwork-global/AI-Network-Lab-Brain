from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote


BRAIN = (
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
    BRAIN
    / "00_CURRENT_STATE"
    / "SECUREBANANA_ROUTE_DUPLICATE_GATE.json"
)

REPORT_FILE = (
    BRAIN
    / "12_REPORTS"
    / "LATEST_SECUREBANANA_ROUTE_DUPLICATE_GATE.md"
)

GITHUB_REPOSITORY = (
    "SecureBananaLabs/bug-bounty"
)

FLOWS = [
    {
        "key": "message",
        "service": "messageService.js",
        "controller": "messageController.js",
        "route_keywords": [
            "messageRoutes",
            "messages",
        ],
        "duplicate_queries": [
            '"message creation" "client-controlled id"',
            '"sendMessage" "payload" "id"',
            '"message service" "server-generated id"',
            '"message creation" "mass assignment"',
            '"message creation" "createdAt"',
        ],
    },
    {
        "key": "notification",
        "service": "notificationService.js",
        "controller": "notificationController.js",
        "route_keywords": [
            "notificationRoutes",
            "notifications",
        ],
        "duplicate_queries": [
            '"notification creation" "client-controlled id"',
            '"createNotification" "payload" "id"',
            '"notification service" "server-owned id"',
            '"notification creation" "mass assignment"',
        ],
    },
    {
        "key": "proposal",
        "service": "proposalService.js",
        "controller": "proposalController.js",
        "route_keywords": [
            "proposalRoutes",
            "proposals",
        ],
        "duplicate_queries": [
            '"proposal creation" "client-controlled id"',
            '"createProposal" "payload" "id"',
            '"proposal service" "server-generated id"',
            '"proposal creation" "mass assignment"',
            '"proposal creation" "createdAt"',
        ],
    },
    {
        "key": "review",
        "service": "reviewService.js",
        "controller": "reviewController.js",
        "route_keywords": [
            "reviewRoutes",
            "reviews",
        ],
        "duplicate_queries": [
            '"review creation" "client-controlled id"',
            '"createReview" "payload" "id"',
            '"review service" "server-generated id"',
            '"review creation" "mass assignment"',
            '"review creation" "createdAt"',
        ],
    },
    {
        "key": "user",
        "service": "userService.js",
        "controller": "userController.js",
        "route_keywords": [
            "userRoutes",
            "users",
        ],
        "duplicate_queries": [
            '"user creation" "client-controlled id"',
            '"createUser" "payload" "id"',
            '"user service" "server-generated id"',
            '"user creation" "mass assignment"',
        ],
    },
]

KNOWN_DUPLICATES = {
    "notification": [
        {
            "number": 2762,
            "title": (
                "Notification creation should preserve "
                "server-owned id and read state"
            ),
            "reason": (
                "Explicitly covers payload overriding "
                "generated notification id and read state."
            ),
        }
    ],
    "user": [
        {
            "number": 802,
            "title": (
                "User creation accepts empty payloads "
                "and client-controlled IDs"
            ),
            "reason": (
                "Explicitly covers payload overriding "
                "generated user id and missing validation."
            ),
        }
    ],
}


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


def relative(path: Path) -> str:
    try:
        return str(
            path.relative_to(REPOSITORY)
        ).replace("\\", "/")
    except ValueError:
        return str(path)


def run_gh_search(
    query: str,
) -> dict[str, Any]:
    complete_query = (
        f"repo:{GITHUB_REPOSITORY} "
        f"is:issue {query}"
    )

    endpoint = (
        "search/issues"
        f"?q={quote(complete_query)}"
        "&per_page=30"
        "&sort=updated"
        "&order=desc"
    )

    process = subprocess.run(
        [
            "gh",
            "api",
            endpoint,
            "--method",
            "GET",
        ],
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )

    if process.returncode != 0:
        return {
            "query": query,
            "success": False,
            "error": (
                process.stderr.strip()
                or process.stdout.strip()
            ),
            "items": [],
        }

    try:
        payload = json.loads(
            process.stdout
        )
    except json.JSONDecodeError as error:
        return {
            "query": query,
            "success": False,
            "error": (
                f"Invalid JSON: {error}"
            ),
            "items": [],
        }

    items = []

    for item in payload.get(
        "items",
        [],
    ):
        items.append({
            "number": item.get("number"),
            "title": item.get("title"),
            "state": item.get("state"),
            "html_url": item.get(
                "html_url"
            ),
            "created_at": item.get(
                "created_at"
            ),
            "updated_at": item.get(
                "updated_at"
            ),
            "body": (
                item.get("body")
                or ""
            )[:6000],
            "pull_request": bool(
                item.get("pull_request")
            ),
        })

    return {
        "query": query,
        "success": True,
        "total_count": payload.get(
            "total_count",
            0,
        ),
        "items": items,
    }


def discover_related_files(
    flow: dict[str, Any],
) -> list[Path]:
    src = (
        REPOSITORY
        / "apps"
        / "api"
        / "src"
    )

    matches: list[Path] = []

    for path in src.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".js",
            ".mjs",
            ".cjs",
            ".ts",
        }:
            continue

        text = read_text(path)

        haystack = (
            path.name.lower()
            + "\n"
            + text.lower()
        )

        terms = [
            flow["key"],
            flow["service"],
            flow["controller"],
            *flow["route_keywords"],
        ]

        if any(
            str(term).lower()
            in haystack
            for term in terms
        ):
            matches.append(path)

    return sorted(
        set(matches)
    )


def inspect_route_security(
    flow: dict[str, Any],
    files: list[Path],
) -> dict[str, Any]:
    combined = "\n\n".join(
        read_text(path)
        for path in files
    )

    route_sources = [
        {
            "file": relative(path),
            "source": read_text(path),
        }
        for path in files
        if (
            "route"
            in path.name.lower()
            or "/routes/"
            in relative(path).lower()
        )
    ]

    auth_patterns = [
        r"\bauthMiddleware\b",
        r"\bauthenticate\b",
        r"\brequireAuth\b",
        r"\bverifyToken\b",
        r"\bprotect\b",
        r"\bauthorize\b",
    ]

    validator_patterns = [
        r"\bvalidate\s*\(",
        r"\bvalidationMiddleware\b",
        r"\bsafeParse\b",
        r"\.parse\s*\(",
        r"\bmatchedData\b",
        r"\bvalidator\b",
    ]

    auth_matches = sorted(
        set(
            match.group(0)
            for pattern in auth_patterns
            for match in re.finditer(
                pattern,
                combined,
                re.IGNORECASE,
            )
        )
    )

    validator_matches = sorted(
        set(
            match.group(0)
            for pattern
            in validator_patterns
            for match in re.finditer(
                pattern,
                combined,
                re.IGNORECASE,
            )
        )
    )

    create_route_lines = []

    for source in route_sources:
        for line_number, line in enumerate(
            source["source"].splitlines(),
            1,
        ):
            if re.search(
                (
                    r"\.(post|put|patch)\s*\("
                    r"|router\.route"
                    r"|create"
                    r"|send"
                ),
                line,
                re.IGNORECASE,
            ):
                create_route_lines.append({
                    "file": source["file"],
                    "line": line_number,
                    "text": line.strip(),
                })

    has_auth = bool(auth_matches)
    has_validator = bool(
        validator_matches
    )

    if (
        has_auth
        and has_validator
    ):
        route_risk = (
            "validated_authenticated"
        )
        impact_weight = 20

    elif has_auth:
        route_risk = (
            "authenticated_without_validation"
        )
        impact_weight = 60

    elif has_validator:
        route_risk = (
            "validated_without_authentication"
        )
        impact_weight = 65

    else:
        route_risk = (
            "no_auth_or_validation_detected"
        )
        impact_weight = 90

    return {
        "related_files": [
            relative(path)
            for path in files
        ],
        "auth_detected": has_auth,
        "auth_matches": auth_matches,
        "validation_detected": (
            has_validator
        ),
        "validation_matches": (
            validator_matches
        ),
        "create_route_lines": (
            create_route_lines
        ),
        "route_risk": route_risk,
        "impact_weight": impact_weight,
    }


def duplicate_relevance(
    flow_key: str,
    item: dict[str, Any],
) -> int:
    text = (
        str(item.get("title") or "")
        + "\n"
        + str(item.get("body") or "")
    ).lower()

    score = 0

    if flow_key in text:
        score += 25

    for phrase in [
        "client-controlled id",
        "server-generated id",
        "server-owned id",
        "override",
        "overrides",
        "mass assignment",
        "...payload",
        "spread",
        "createdat",
        "sentat",
        "read state",
        "unexpected field",
    ]:
        if phrase in text:
            score += 10

    if (
        "parent bounty"
        in text
        and "#743"
        in text
    ):
        score += 10

    return min(
        score,
        100,
    )


results: list[dict[str, Any]] = []

for flow in FLOWS:
    related_files = (
        discover_related_files(flow)
    )

    route_inspection = (
        inspect_route_security(
            flow,
            related_files,
        )
    )

    search_runs = [
        run_gh_search(query)
        for query
        in flow["duplicate_queries"]
    ]

    issue_map: dict[int, dict[str, Any]] = {}

    for search_run in search_runs:
        for item in search_run["items"]:
            number = item.get("number")

            if not isinstance(
                number,
                int,
            ):
                continue

            relevance = duplicate_relevance(
                flow["key"],
                item,
            )

            existing = issue_map.get(number)

            enriched = {
                **item,
                "relevance": relevance,
            }

            if (
                existing is None
                or relevance
                > existing["relevance"]
            ):
                issue_map[number] = (
                    enriched
                )

    duplicates = sorted(
        issue_map.values(),
        key=lambda item: (
            item["relevance"],
            item.get("updated_at") or "",
        ),
        reverse=True,
    )

    strong_duplicates = [
        item
        for item in duplicates
        if item["relevance"] >= 45
    ]

    known_duplicates = (
        KNOWN_DUPLICATES.get(
            flow["key"],
            [],
        )
    )

    duplicate_blocked = bool(
        strong_duplicates
        or known_duplicates
    )

    if duplicate_blocked:
        decision = (
            "DUPLICATE_OR_OCCUPIED"
        )
        candidate_score = 0

    else:
        decision = (
            "AVAILABLE_FOR_DEEPER_LOCAL_PROOF"
        )

        candidate_score = (
            route_inspection[
                "impact_weight"
            ]
        )

    results.append({
        "flow": flow["key"],
        "route_inspection": (
            route_inspection
        ),
        "search_runs": search_runs,
        "duplicate_candidates": (
            duplicates[:20]
        ),
        "strong_duplicates": (
            strong_duplicates[:10]
        ),
        "known_duplicates": (
            known_duplicates
        ),
        "duplicate_blocked": (
            duplicate_blocked
        ),
        "decision": decision,
        "candidate_score": (
            candidate_score
        ),
    })


available = [
    result
    for result in results
    if not result[
        "duplicate_blocked"
    ]
]

available.sort(
    key=lambda item: (
        item["candidate_score"],
        1
        if not item["route_inspection"][
            "auth_detected"
        ]
        else 0,
        1
        if not item["route_inspection"][
            "validation_detected"
        ]
        else 0,
    ),
    reverse=True,
)

recommended = (
    available[0]
    if available
    else None
)

if recommended:
    overall_decision = (
        "CANDIDATE_AVAILABLE"
    )

    next_action = (
        "build_route_level_local_proof_for_"
        + recommended["flow"]
    )

else:
    overall_decision = (
        "ALL_TESTED_BODY_FLOWS_OCCUPIED"
    )

    next_action = (
        "move_to_next_static_candidate_class"
    )

state = {
    "generated_at": utc_now(),
    "repository": str(REPOSITORY),
    "github_repository": (
        GITHUB_REPOSITORY
    ),
    "overall_decision": (
        overall_decision
    ),
    "recommended_candidate": (
        recommended
    ),
    "recommended_next_action": (
        next_action
    ),
    "results": results,
    "github_access_mode": (
        "read_only_search"
    ),
    "source_modified": False,
    "dependency_install_performed": False,
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
        "Route and Duplicate Gate"
    ),
    "",
    f"Gerado em: {state['generated_at']}",
    "",
    "## Resultado",
    "",
    (
        "- Decisão: "
        f"**{overall_decision}**"
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
            "- Fluxo: "
            f"**{recommended['flow']}**"
        ),
        (
            "- Candidate score: "
            f"**{recommended['candidate_score']}**"
        ),
        (
            "- Route risk: "
            f"**{recommended['route_inspection']['route_risk']}**"
        ),
        "",
    ])

lines.extend([
    "## Resultados por fluxo",
    "",
])

for result in results:
    inspection = (
        result["route_inspection"]
    )

    lines.extend([
        f"### {result['flow']}",
        "",
        (
            "- Decisão: "
            f"**{result['decision']}**"
        ),
        (
            "- Autenticação detectada: "
            f"**{inspection['auth_detected']}**"
        ),
        (
            "- Validação detectada: "
            f"**{inspection['validation_detected']}**"
        ),
        (
            "- Route risk: "
            f"**{inspection['route_risk']}**"
        ),
        (
            "- Duplicata bloqueadora: "
            f"**{result['duplicate_blocked']}**"
        ),
        (
            "- Duplicatas conhecidas: "
            f"**{len(result['known_duplicates'])}**"
        ),
        (
            "- Correspondências fortes: "
            f"**{len(result['strong_duplicates'])}**"
        ),
        "",
        "#### Rotas identificadas",
        "",
    ])

    for route in inspection[
        "create_route_lines"
    ]:
        lines.append(
            "- "
            f"`{route['file']}:{route['line']}` "
            f"— `{route['text']}`"
        )

    if not inspection[
        "create_route_lines"
    ]:
        lines.append(
            "- Nenhuma linha de criação identificada."
        )

    lines.extend([
        "",
        "#### Duplicatas conhecidas",
        "",
    ])

    for item in result[
        "known_duplicates"
    ]:
        lines.append(
            f"- #{item['number']} — "
            f"{item['title']}"
        )

    if not result[
        "known_duplicates"
    ]:
        lines.append(
            "- Nenhuma duplicata pré-confirmada."
        )

    lines.extend([
        "",
        "#### Correspondências online fortes",
        "",
    ])

    for item in result[
        "strong_duplicates"
    ]:
        lines.append(
            f"- #{item['number']} — "
            f"{item['title']} "
            f"(relevância {item['relevance']})"
        )

    if not result[
        "strong_duplicates"
    ]:
        lines.append(
            "- Nenhuma correspondência forte encontrada."
        )

    lines.append("")

lines.extend([
    "## Segurança operacional",
    "",
    "- Pesquisa GitHub: **somente leitura**",
    "- Código original alterado: **não**",
    "- Dependências instaladas: **não**",
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
    "===== ROUTE AND DUPLICATE GATE ====="
)
print(
    "Overall decision:",
    overall_decision,
)
print(
    "Recommended next action:",
    next_action,
)

for result in results:
    inspection = (
        result["route_inspection"]
    )

    print()
    print(
        "Flow:",
        result["flow"],
    )
    print(
        "  Authentication detected:",
        inspection["auth_detected"],
    )
    print(
        "  Validation detected:",
        inspection[
            "validation_detected"
        ],
    )
    print(
        "  Route risk:",
        inspection["route_risk"],
    )
    print(
        "  Known duplicates:",
        len(
            result[
                "known_duplicates"
            ]
        ),
    )
    print(
        "  Strong online matches:",
        len(
            result[
                "strong_duplicates"
            ]
        ),
    )
    print(
        "  Duplicate blocked:",
        result[
            "duplicate_blocked"
        ],
    )
    print(
        "  Decision:",
        result["decision"],
    )
    print(
        "  Candidate score:",
        result[
            "candidate_score"
        ],
    )

    for item in result[
        "known_duplicates"
    ]:
        print(
            "  Known issue:",
            f"#{item['number']}",
            item["title"],
        )

    for item in result[
        "strong_duplicates"
    ][:5]:
        print(
            "  Online match:",
            f"#{item['number']}",
            item["title"],
            f"(relevance {item['relevance']})",
        )

if recommended:
    print()
    print(
        "===== RECOMMENDED AVAILABLE FLOW ====="
    )
    print(
        "Flow:",
        recommended["flow"],
    )
    print(
        "Route risk:",
        recommended[
            "route_inspection"
        ]["route_risk"],
    )
    print(
        "Authentication detected:",
        recommended[
            "route_inspection"
        ]["auth_detected"],
    )
    print(
        "Validation detected:",
        recommended[
            "route_inspection"
        ]["validation_detected"],
    )
    print(
        "Candidate score:",
        recommended[
            "candidate_score"
        ],
    )

print()
print(
    "===== ROUTE AND DUPLICATE GATE SAFETY ====="
)
print("GitHub search mode: read only")
print("Original source modified: no")
print("Dependency install performed: no")
print("External publication performed: no")
print("Issue created: no")
print("Comment created: no")
print("Fork created: no")
print("Pull request created: no")
print("Report:", REPORT_FILE)
