from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

DATABASE = (
    ROOT
    / "11_DATA"
    / "global_revenue_brain.db"
)

PLANS_DIRECTORY = (
    ROOT
    / "07_EXECUTION_PLANS"
)

CSV_PATH = (
    ROOT
    / "04_OPPORTUNITIES"
    / "execution_plan_queue.csv"
)

REPORT_PATH = (
    ROOT
    / "12_REPORTS"
    / "LATEST_EXECUTION_PLANNER.md"
)

MAX_PLANS_PER_RUN = 5
MINIMUM_PAYMENT_PROBABILITY = 60.0


TECHNOLOGY_PATTERNS = {
    "PowerShell": (
        "powershell",
        ".ps1",
        "windows shell",
    ),
    "Python": (
        "python",
        ".py",
        "pytest",
        "pip",
    ),
    "JavaScript": (
        "javascript",
        "node.js",
        "nodejs",
        "npm",
        "yarn",
        ".js",
    ),
    "TypeScript": (
        "typescript",
        ".ts",
        "tsx",
    ),
    "React": (
        "react",
        "jsx",
        "component",
    ),
    "API": (
        "api",
        "endpoint",
        "request",
        "response",
        "rest",
        "graphql",
    ),
    "Database": (
        "database",
        "sqlite",
        "postgres",
        "sql",
        "migration",
        "schema",
    ),
    "GitHub": (
        "github",
        "pull request",
        "repository",
        "issue",
        "branch",
    ),
    "Testing": (
        "test",
        "tests",
        "testing",
        "regression",
        "unit test",
        "integration test",
    ),
    "Documentation": (
        "documentation",
        "readme",
        "docs",
        "guide",
    ),
    "Docker": (
        "docker",
        "dockerfile",
        "container",
    ),
    "Payments": (
        "stripe",
        "paypal",
        "payment",
        "subscription",
        "billing",
        "refund",
        "dispute",
    ),
}


DELIVERABLE_PATTERNS = {
    "pull_request": (
        "pull request",
        "submit a pr",
        "open a pr",
        "merge request",
    ),
    "code_patch": (
        "patch",
        "fix",
        "implement",
        "implementation",
        "code change",
    ),
    "tests": (
        "test",
        "tests",
        "regression test",
        "unit test",
    ),
    "documentation": (
        "documentation",
        "readme",
        "docs",
    ),
    "report": (
        "report",
        "findings",
        "analysis",
        "audit",
    ),
    "proof_of_concept": (
        "proof of concept",
        "poc",
        "reproduction",
        "reproduce",
    ),
}


RISK_PATTERNS = {
    "unclear_acceptance": (
        "to be discussed",
        "details later",
        "tbd",
        "unclear",
    ),
    "security_sensitive": (
        "exploit",
        "vulnerability",
        "security",
        "authentication",
        "authorization",
    ),
    "financial_logic": (
        "payment",
        "billing",
        "refund",
        "dispute",
        "subscription",
    ),
    "large_scope": (
        "complete rewrite",
        "entire application",
        "all modules",
        "production readiness",
    ),
    "external_dependency": (
        "third-party",
        "external service",
        "vendor api",
        "cloud account",
    ),
}


PROHIBITED_OR_DANGEROUS_PATTERNS = (
    "steal credentials",
    "bypass payment",
    "credential theft",
    "phishing",
    "malware",
    "ransomware",
    "private key",
    "seed phrase",
    "unauthorized access",
)


def utc_now() -> str:
    return datetime.now(
        timezone.utc
    ).isoformat()


def normalize(value: Any) -> str:
    return re.sub(
        r"\s+",
        " ",
        str(value or ""),
    ).strip()


def normalized_lower(value: Any) -> str:
    return normalize(value).lower()


def slugify(value: str) -> str:
    cleaned = re.sub(
        r"[^a-zA-Z0-9]+",
        "-",
        value,
    ).strip("-").lower()

    return cleaned[:90] or "task"


def table_exists(
    conn: sqlite3.Connection,
    table: str,
) -> bool:
    return bool(
        conn.execute(
            """
            SELECT COUNT(*)
            FROM sqlite_master
            WHERE type='table'
              AND name=?
            """,
            (table,),
        ).fetchone()[0]
    )


def table_columns(
    conn: sqlite3.Connection,
    table: str,
) -> set[str]:
    return {
        str(row[1])
        for row in conn.execute(
            f'PRAGMA table_info("{table}")'
        ).fetchall()
    }


def first_available(
    row: sqlite3.Row,
    names: tuple[str, ...],
    default: Any = None,
) -> Any:
    keys = set(row.keys())

    for name in names:
        if name in keys:
            value = row[name]

            if value not in (None, ""):
                return value

    return default


def find_matches(
    text: str,
    mapping: dict[str, tuple[str, ...]],
) -> list[str]:
    lowered = text.lower()

    return [
        label
        for label, patterns in mapping.items()
        if any(
            pattern in lowered
            for pattern in patterns
        )
    ]


def extract_bullets(
    text: str,
    maximum: int = 12,
) -> list[str]:
    results: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()

        line = re.sub(
            r"^[-*+]\s+",
            "",
            line,
        )

        line = re.sub(
            r"^\d+[.)]\s+",
            "",
            line,
        )

        if len(line) < 12:
            continue

        lowered = line.lower()

        if any(
            token in lowered
            for token in (
                "must",
                "should",
                "required",
                "acceptance",
                "deliverable",
                "implement",
                "fix",
                "test",
                "submit",
                "expected",
                "criteria",
            )
        ):
            results.append(
                line[:500]
            )

        if len(results) >= maximum:
            break

    return results


def extract_urls(text: str) -> list[str]:
    urls = re.findall(
        r"https?://[^\s)\]>\"']+",
        text,
    )

    unique: list[str] = []

    for url in urls:
        cleaned = url.rstrip(
            ".,;:"
        )

        if cleaned not in unique:
            unique.append(cleaned)

    return unique[:20]


def load_cached_issue(
    conn: sqlite3.Connection,
    candidate_key: str,
) -> dict[str, Any] | None:
    if not table_exists(
        conn,
        "paid_task_api_cache",
    ):
        return None

    row = conn.execute(
        """
        SELECT response_json
        FROM paid_task_api_cache
        WHERE candidate_key = ?
        """,
        (candidate_key,),
    ).fetchone()

    if not row or not row[0]:
        return None

    try:
        return json.loads(
            row[0]
        )
    except json.JSONDecodeError:
        return None


def create_execution_steps(
    *,
    technologies: list[str],
    deliverables: list[str],
    acceptance_requirements: list[str],
    repository: str,
    issue_number: int | None,
) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []

    steps.append({
        "order": 1,
        "name": "Confirmar regras de participação",
        "objective": (
            "Confirmar que a tarefa continua aberta, "
            "que a recompensa está disponível e que o "
            "executor pode participar."
        ),
        "commands_or_actions": [
            "Abrir a issue e revisar comentários recentes.",
            "Confirmar processo de claim, prazo e critérios de pagamento.",
            "Não iniciar trabalho antes da aprovação humana.",
        ],
        "external_action": False,
        "human_approval_required": True,
    })

    steps.append({
        "order": 2,
        "name": "Preparar workspace isolado",
        "objective": (
            "Criar uma cópia local isolada do repositório "
            "sem alterar projetos existentes."
        ),
        "commands_or_actions": [
            (
                "Criar pasta de trabalho específica para "
                f"{repository or 'o repositório'}."
            ),
            "Clonar ou fazer fork somente após autorização humana.",
            "Criar branch exclusiva para a tarefa.",
            "Registrar commit inicial e versão da dependência.",
        ],
        "external_action": False,
        "human_approval_required": True,
    })

    steps.append({
        "order": 3,
        "name": "Reproduzir e delimitar o problema",
        "objective": (
            "Reproduzir o comportamento descrito e identificar "
            "o menor escopo técnico capaz de atender à issue."
        ),
        "commands_or_actions": [
            "Instalar dependências conforme documentação oficial.",
            "Executar testes existentes antes de modificar código.",
            "Criar reprodução mínima ou teste que falhe.",
            "Registrar arquivos e componentes envolvidos.",
        ],
        "external_action": False,
        "human_approval_required": False,
    })

    implementation_actions = [
        "Implementar a menor alteração que satisfaça os critérios.",
        "Evitar alterações não relacionadas à tarefa.",
        "Manter compatibilidade com padrões existentes do repositório.",
    ]

    if technologies:
        implementation_actions.append(
            "Tecnologias detectadas: "
            + ", ".join(technologies)
            + "."
        )

    steps.append({
        "order": 4,
        "name": "Implementar solução",
        "objective": (
            "Produzir a correção, automação ou entrega técnica "
            "com escopo controlado."
        ),
        "commands_or_actions": implementation_actions,
        "external_action": False,
        "human_approval_required": False,
    })

    test_actions = [
        "Executar testes existentes relevantes.",
        "Adicionar teste de regressão quando aplicável.",
        "Executar análise estática, lint ou compilação.",
        "Registrar comandos executados e resultados.",
    ]

    if "tests" not in deliverables:
        test_actions.append(
            "Mesmo sem teste explicitamente solicitado, "
            "produzir evidência verificável da solução."
        )

    steps.append({
        "order": 5,
        "name": "Validar tecnicamente",
        "objective": (
            "Comprovar que a entrega funciona e não introduz "
            "regressões conhecidas."
        ),
        "commands_or_actions": test_actions,
        "external_action": False,
        "human_approval_required": False,
    })

    acceptance_actions = [
        "Comparar a implementação com cada critério de aceite.",
        "Preparar resumo das alterações e evidências de teste.",
        "Documentar limitações e riscos remanescentes.",
    ]

    for requirement in acceptance_requirements[:8]:
        acceptance_actions.append(
            "Validar requisito: "
            + requirement
        )

    steps.append({
        "order": 6,
        "name": "Preparar pacote de entrega",
        "objective": (
            "Preparar a entrega para revisão humana antes de "
            "qualquer publicação externa."
        ),
        "commands_or_actions": acceptance_actions,
        "external_action": False,
        "human_approval_required": True,
    })

    steps.append({
        "order": 7,
        "name": "Submeter após aprovação",
        "objective": (
            "Publicar claim, comentário, fork ou pull request "
            "somente após autorização expressa."
        ),
        "commands_or_actions": [
            (
                f"Referenciar a issue #{issue_number}."
                if issue_number
                else "Referenciar a oportunidade original."
            ),
            "Publicar somente o conteúdo aprovado.",
            "Não prometer prazo, resultado ou pagamento.",
            "Salvar URL e horário da submissão.",
        ],
        "external_action": True,
        "human_approval_required": True,
    })

    steps.append({
        "order": 8,
        "name": "Acompanhar aceite e pagamento",
        "objective": (
            "Registrar revisão, aceite, pedido de alteração "
            "e eventual pagamento."
        ),
        "commands_or_actions": [
            "Monitorar respostas do mantenedor ou contratante.",
            "Registrar solicitações de mudança.",
            "Confirmar método de pagamento antes de fornecer dados.",
            "Registrar pagamento somente mediante evidência real.",
        ],
        "external_action": True,
        "human_approval_required": True,
    })

    return steps


def calculate_plan_readiness(
    *,
    payment_probability: float,
    reward_amount: float,
    claim_found: bool,
    payment_found: bool,
    acceptance_requirements: list[str],
    technologies: list[str],
    prohibited: list[str],
) -> tuple[float, str, list[str]]:
    score = 0.0
    reasons: list[str] = []

    score += payment_probability * 0.40

    if reward_amount > 0:
        score += 15
        reasons.append(
            "Recompensa numérica disponível."
        )

    if claim_found:
        score += 15
        reasons.append(
            "Processo de claim ou entrega identificado."
        )
    else:
        reasons.append(
            "Processo de claim ainda exige confirmação."
        )

    if payment_found:
        score += 12
        reasons.append(
            "Promessa de pagamento identificada."
        )
    else:
        reasons.append(
            "Termos de pagamento ainda exigem confirmação."
        )

    if acceptance_requirements:
        score += min(
            len(acceptance_requirements) * 2,
            10,
        )
        reasons.append(
            "Critérios técnicos extraídos da descrição."
        )
    else:
        reasons.append(
            "Critérios de aceite não foram extraídos claramente."
        )

    if technologies:
        score += 8
        reasons.append(
            "Stack técnica identificada."
        )

    if prohibited:
        score = 0
        reasons.append(
            "Conteúdo incompatível com execução segura detectado."
        )

    score = round(
        max(0, min(100, score)),
        2,
    )

    if prohibited:
        status = "blocked_safety_review"

    elif (
        payment_probability >= 80
        and reward_amount > 0
        and claim_found
        and payment_found
        and score >= 75
    ):
        status = "ready_for_human_approval"

    elif (
        payment_probability >= 60
        and reward_amount > 0
    ):
        status = "requirements_review_required"

    else:
        status = "not_ready"

    return score, status, reasons


conn = sqlite3.connect(
    DATABASE
)

conn.row_factory = sqlite3.Row

required_tables = (
    "payment_probability_ranking",
    "verified_paid_tasks",
)

for table in required_tables:
    if not table_exists(
        conn,
        table,
    ):
        raise RuntimeError(
            f"Tabela obrigatória ausente: {table}"
        )

conn.executescript(
    """
    CREATE TABLE IF NOT EXISTS paid_task_execution_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_key TEXT NOT NULL UNIQUE,
        candidate_key TEXT NOT NULL UNIQUE,
        title TEXT NOT NULL,
        organization TEXT,
        source_url TEXT NOT NULL,
        repository TEXT,
        issue_number INTEGER,
        reward_amount REAL,
        reward_currency TEXT,
        payment_probability REAL,
        expected_cash_value REAL,
        estimated_hours REAL,
        adjusted_value_per_hour REAL,
        technologies_json TEXT NOT NULL,
        deliverables_json TEXT NOT NULL,
        acceptance_requirements_json TEXT NOT NULL,
        risks_json TEXT NOT NULL,
        external_urls_json TEXT NOT NULL,
        execution_steps_json TEXT NOT NULL,
        readiness_score REAL NOT NULL,
        planning_status TEXT NOT NULL,
        planning_reason TEXT NOT NULL,
        human_approval_required INTEGER
            NOT NULL DEFAULT 1,
        external_action_performed INTEGER
            NOT NULL DEFAULT 0,
        claim_performed INTEGER
            NOT NULL DEFAULT 0,
        code_submitted INTEGER
            NOT NULL DEFAULT 0,
        plan_file TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS
    idx_execution_plan_status
    ON paid_task_execution_plans(
        planning_status,
        readiness_score DESC,
        adjusted_value_per_hour DESC
    );
    """
)

ranking_columns = table_columns(
    conn,
    "payment_probability_ranking",
)

query = """
    SELECT
        p.*,
        v.payment_promise_found,
        v.claim_mechanism_found,
        v.github_issue_state,
        v.github_owner,
        v.github_repository,
        v.github_issue_number,
        v.truth_status,
        v.truth_reason
    FROM payment_probability_ranking p
    JOIN verified_paid_tasks v
      ON v.candidate_key = p.candidate_key
    LEFT JOIN paid_task_execution_plans e
      ON e.candidate_key = p.candidate_key
    WHERE p.payment_probability >= ?
      AND p.reward_amount > 0
      AND p.recommended_action IN (
          'prepare_execution_plan',
          'verify_claim_and_payment_terms'
      )
      AND (
          e.candidate_key IS NULL
          OR e.planning_status IN (
              'requirements_review_required',
              'not_ready'
          )
      )
    ORDER BY
        p.final_priority DESC,
        p.payment_probability DESC,
        p.probability_adjusted_value_per_hour DESC
    LIMIT ?
"""

candidates = conn.execute(
    query,
    (
        MINIMUM_PAYMENT_PROBABILITY,
        MAX_PLANS_PER_RUN,
    ),
).fetchall()

print()
print("===== EXECUTION PLANNER =====")
print("Candidates selected:", len(candidates))
print(
    "Minimum payment probability:",
    MINIMUM_PAYMENT_PROBABILITY,
)

PLANS_DIRECTORY.mkdir(
    parents=True,
    exist_ok=True,
)

created_plans: list[dict[str, Any]] = []
now = utc_now()

for row in candidates:
    candidate_key = str(
        row["candidate_key"]
    )

    issue = load_cached_issue(
        conn,
        candidate_key,
    ) or {}

    title = normalize(
        issue.get("title")
        or row["title"]
    )

    body = str(
        issue.get("body")
        or ""
    )

    labels = [
        normalize(
            label.get("name")
        )
        for label in (
            issue.get("labels")
            or []
        )
        if isinstance(label, dict)
    ]

    combined_text = (
        title
        + "\n"
        + body
        + "\n"
        + " ".join(labels)
    )

    technologies = find_matches(
        combined_text,
        TECHNOLOGY_PATTERNS,
    )

    deliverables = find_matches(
        combined_text,
        DELIVERABLE_PATTERNS,
    )

    risk_categories = find_matches(
        combined_text,
        RISK_PATTERNS,
    )

    acceptance_requirements = (
        extract_bullets(
            body
        )
    )

    external_urls = extract_urls(
        body
    )

    lowered = combined_text.lower()

    prohibited = [
        term
        for term in PROHIBITED_OR_DANGEROUS_PATTERNS
        if term in lowered
    ]

    owner = normalize(
        row["github_owner"]
    )

    repository_name = normalize(
        row["github_repository"]
    )

    repository = (
        f"{owner}/{repository_name}"
        if owner and repository_name
        else normalize(
            row["organization"]
        )
    )

    issue_number = first_available(
        row,
        (
            "github_issue_number",
        ),
    )

    reward_amount = float(
        row["reward_amount"]
        or 0
    )

    payment_probability = float(
        row["payment_probability"]
        or 0
    )

    estimated_hours = float(
        row["estimated_hours"]
        or 0
    )

    adjusted_value_per_hour = float(
        first_available(
            row,
            (
                "probability_adjusted_value_per_hour",
                "estimated_value_per_hour",
            ),
            0,
        )
        or 0
    )

    expected_cash_value = float(
        row["expected_cash_value"]
        or 0
    )

    claim_found = bool(
        row["claim_mechanism_found"]
    )

    payment_found = bool(
        row["payment_promise_found"]
    )

    steps = create_execution_steps(
        technologies=technologies,
        deliverables=deliverables,
        acceptance_requirements=(
            acceptance_requirements
        ),
        repository=repository,
        issue_number=issue_number,
    )

    (
        readiness_score,
        planning_status,
        planning_reasons,
    ) = calculate_plan_readiness(
        payment_probability=(
            payment_probability
        ),
        reward_amount=reward_amount,
        claim_found=claim_found,
        payment_found=payment_found,
        acceptance_requirements=(
            acceptance_requirements
        ),
        technologies=technologies,
        prohibited=prohibited,
    )

    if risk_categories:
        planning_reasons.append(
            "Riscos técnicos detectados: "
            + ", ".join(risk_categories)
            + "."
        )

    if prohibited:
        risk_categories.extend(
            [
                "blocked:"
                + item
                for item in prohibited
            ]
        )

    plan_key = hashlib.sha256(
        (
            candidate_key
            + "|"
            + title
            + "|"
            + str(issue.get("updated_at") or "")
        ).encode("utf-8")
    ).hexdigest()

    filename = (
        slugify(repository)
        + "-"
        + (
            f"issue-{issue_number}"
            if issue_number
            else slugify(title)
        )
        + ".md"
    )

    plan_path = (
        PLANS_DIRECTORY
        / filename
    )

    markdown = [
        f"# Execution Plan — {title}",
        "",
        f"Gerado em: {now}",
        "",
        "## Controle",
        "",
        f"- Status: **{planning_status}**",
        f"- Readiness score: **{readiness_score}**",
        "- Aprovação humana obrigatória: **sim**",
        "- Claim realizado: **não**",
        "- Código submetido: **não**",
        "- Ação externa realizada: **não**",
        "",
        "## Oportunidade",
        "",
        f"- Solicitante: {row['organization']}",
        f"- Repositório: {repository}",
        f"- Issue: #{issue_number}",
        f"- URL: {row['url']}",
        f"- Estado da issue: {row['github_issue_state']}",
        f"- Truth status: {row['truth_status']}",
        "",
        "## Retorno financeiro estimado",
        "",
        f"- Recompensa: "
        f"{row['reward_currency'] or '?'} "
        f"{reward_amount}",
        f"- Probabilidade de pagamento: "
        f"{payment_probability}%",
        f"- Valor esperado ajustado: "
        f"{row['reward_currency'] or '?'} "
        f"{expected_cash_value}",
        f"- Horas estimadas: {estimated_hours}",
        f"- Valor/hora ajustado: "
        f"{adjusted_value_per_hour}",
        "",
        "## Tecnologias detectadas",
        "",
    ]

    if technologies:
        markdown.extend(
            f"- {item}"
            for item in technologies
        )
    else:
        markdown.append(
            "- Stack ainda não identificada claramente."
        )

    markdown.extend([
        "",
        "## Entregáveis detectados",
        "",
    ])

    if deliverables:
        markdown.extend(
            f"- {item}"
            for item in deliverables
        )
    else:
        markdown.append(
            "- Entregáveis exigem confirmação."
        )

    markdown.extend([
        "",
        "## Critérios e requisitos extraídos",
        "",
    ])

    if acceptance_requirements:
        markdown.extend(
            f"- {item}"
            for item in acceptance_requirements
        )
    else:
        markdown.append(
            "- Nenhum critério explícito foi extraído; "
            "revisão manual necessária."
        )

    markdown.extend([
        "",
        "## Riscos",
        "",
    ])

    if risk_categories:
        markdown.extend(
            f"- {item}"
            for item in sorted(
                set(risk_categories)
            )
        )
    else:
        markdown.append(
            "- Nenhum risco textual crítico detectado."
        )

    markdown.extend([
        "",
        "## Motivos da classificação",
        "",
    ])

    markdown.extend(
        f"- {item}"
        for item in planning_reasons
    )

    markdown.extend([
        "",
        "## Plano técnico",
        "",
    ])

    for step in steps:
        markdown.extend([
            f"### {step['order']}. "
            f"{step['name']}",
            "",
            step["objective"],
            "",
        ])

        for action in step[
            "commands_or_actions"
        ]:
            markdown.append(
                f"- {action}"
            )

        markdown.extend([
            "",
            "- Ação externa: "
            + (
                "sim"
                if step["external_action"]
                else "não"
            ),
            "- Aprovação humana: "
            + (
                "obrigatória"
                if step[
                    "human_approval_required"
                ]
                else "não exigida nesta etapa"
            ),
            "",
        ])

    markdown.extend([
        "## Próximo gate",
        "",
        (
            "Confirmar manualmente os termos de claim e pagamento "
            "antes de clonar, fazer fork, comentar ou iniciar trabalho."
        ),
        "",
        "## Descrição original armazenada",
        "",
        "```text",
        body[:20000],
        "```",
        "",
    ])

    plan_path.write_text(
        "\n".join(markdown),
        encoding="utf-8",
    )

    conn.execute(
        """
        INSERT INTO paid_task_execution_plans (
            plan_key,
            candidate_key,
            title,
            organization,
            source_url,
            repository,
            issue_number,
            reward_amount,
            reward_currency,
            payment_probability,
            expected_cash_value,
            estimated_hours,
            adjusted_value_per_hour,
            technologies_json,
            deliverables_json,
            acceptance_requirements_json,
            risks_json,
            external_urls_json,
            execution_steps_json,
            readiness_score,
            planning_status,
            planning_reason,
            human_approval_required,
            external_action_performed,
            claim_performed,
            code_submitted,
            plan_file,
            created_at,
            updated_at
        )
        VALUES (
            ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
            ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, 0, 0, ?, ?, ?
        )
        ON CONFLICT(candidate_key) DO UPDATE SET
            plan_key =
                excluded.plan_key,
            title =
                excluded.title,
            organization =
                excluded.organization,
            source_url =
                excluded.source_url,
            repository =
                excluded.repository,
            issue_number =
                excluded.issue_number,
            reward_amount =
                excluded.reward_amount,
            reward_currency =
                excluded.reward_currency,
            payment_probability =
                excluded.payment_probability,
            expected_cash_value =
                excluded.expected_cash_value,
            estimated_hours =
                excluded.estimated_hours,
            adjusted_value_per_hour =
                excluded.adjusted_value_per_hour,
            technologies_json =
                excluded.technologies_json,
            deliverables_json =
                excluded.deliverables_json,
            acceptance_requirements_json =
                excluded.acceptance_requirements_json,
            risks_json =
                excluded.risks_json,
            external_urls_json =
                excluded.external_urls_json,
            execution_steps_json =
                excluded.execution_steps_json,
            readiness_score =
                excluded.readiness_score,
            planning_status =
                excluded.planning_status,
            planning_reason =
                excluded.planning_reason,
            human_approval_required = 1,
            external_action_performed = 0,
            claim_performed = 0,
            code_submitted = 0,
            plan_file =
                excluded.plan_file,
            updated_at =
                excluded.updated_at
        """,
        (
            plan_key,
            candidate_key,
            title,
            row["organization"],
            row["url"],
            repository,
            issue_number,
            reward_amount,
            row["reward_currency"],
            payment_probability,
            expected_cash_value,
            estimated_hours,
            adjusted_value_per_hour,
            json.dumps(
                technologies,
                ensure_ascii=False,
            ),
            json.dumps(
                deliverables,
                ensure_ascii=False,
            ),
            json.dumps(
                acceptance_requirements,
                ensure_ascii=False,
            ),
            json.dumps(
                sorted(
                    set(risk_categories)
                ),
                ensure_ascii=False,
            ),
            json.dumps(
                external_urls,
                ensure_ascii=False,
            ),
            json.dumps(
                steps,
                ensure_ascii=False,
            ),
            readiness_score,
            planning_status,
            "; ".join(
                planning_reasons
            ),
            str(
                plan_path.relative_to(ROOT)
            ),
            now,
            now,
        ),
    )

    conn.execute(
        """
        UPDATE payment_probability_ranking
        SET planning_status = ?
        WHERE candidate_key = ?
        """,
        (
            planning_status,
            candidate_key,
        ),
    )

    created_plans.append({
        "title": title,
        "organization": row["organization"],
        "repository": repository,
        "issue_number": issue_number,
        "reward_currency": row["reward_currency"],
        "reward_amount": reward_amount,
        "payment_probability": (
            payment_probability
        ),
        "expected_cash_value": (
            expected_cash_value
        ),
        "adjusted_value_per_hour": (
            adjusted_value_per_hour
        ),
        "readiness_score": (
            readiness_score
        ),
        "planning_status": (
            planning_status
        ),
        "plan_file": str(
            plan_path.relative_to(ROOT)
        ),
        "url": row["url"],
    })

conn.commit()

all_plans = conn.execute(
    """
    SELECT *
    FROM paid_task_execution_plans
    ORDER BY
        CASE planning_status
            WHEN 'ready_for_human_approval'
            THEN 1
            WHEN 'requirements_review_required'
            THEN 2
            WHEN 'not_ready'
            THEN 3
            ELSE 4
        END,
        readiness_score DESC,
        adjusted_value_per_hour DESC,
        expected_cash_value DESC
    """
).fetchall()

counts = {
    row["planning_status"]: row["total"]
    for row in conn.execute(
        """
        SELECT
            planning_status,
            COUNT(*) AS total
        FROM paid_task_execution_plans
        GROUP BY planning_status
        """
    ).fetchall()
}

CSV_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

fields = [
    "title",
    "organization",
    "repository",
    "issue_number",
    "reward_currency",
    "reward_amount",
    "payment_probability",
    "expected_cash_value",
    "estimated_hours",
    "adjusted_value_per_hour",
    "readiness_score",
    "planning_status",
    "planning_reason",
    "plan_file",
    "source_url",
]

with CSV_PATH.open(
    "w",
    encoding="utf-8-sig",
    newline="",
) as file:
    writer = csv.DictWriter(
        file,
        fieldnames=fields,
    )

    writer.writeheader()

    for row in all_plans:
        writer.writerow({
            "title": row["title"],
            "organization": row["organization"],
            "repository": row["repository"],
            "issue_number": row["issue_number"],
            "reward_currency": row["reward_currency"],
            "reward_amount": row["reward_amount"],
            "payment_probability": (
                row["payment_probability"]
            ),
            "expected_cash_value": (
                row["expected_cash_value"]
            ),
            "estimated_hours": (
                row["estimated_hours"]
            ),
            "adjusted_value_per_hour": (
                row["adjusted_value_per_hour"]
            ),
            "readiness_score": (
                row["readiness_score"]
            ),
            "planning_status": (
                row["planning_status"]
            ),
            "planning_reason": (
                row["planning_reason"]
            ),
            "plan_file": row["plan_file"],
            "source_url": row["source_url"],
        })

REPORT_PATH.parent.mkdir(
    parents=True,
    exist_ok=True,
)

lines = [
    "# Global Revenue Brain — Execution Planner",
    "",
    f"Gerado em: {utc_now()}",
    "",
    "Nenhum claim, comentário, fork ou código foi publicado.",
    "",
    "## Resumo",
    "",
    f"- Planos criados nesta rodada: "
    f"**{len(created_plans)}**",
    f"- Prontos para aprovação humana: "
    f"**{counts.get('ready_for_human_approval', 0)}**",
    f"- Revisão de requisitos necessária: "
    f"**{counts.get('requirements_review_required', 0)}**",
    f"- Não prontos: "
    f"**{counts.get('not_ready', 0)}**",
    f"- Bloqueados para revisão de segurança: "
    f"**{counts.get('blocked_safety_review', 0)}**",
    "",
    "## Ranking dos planos",
    "",
]

for index, row in enumerate(
    all_plans[:30],
    1,
):
    lines.extend([
        f"### {index}. {row['title']}",
        "",
        f"- Solicitante: {row['organization']}",
        f"- Repositório: {row['repository']}",
        f"- Issue: #{row['issue_number']}",
        f"- Recompensa: "
        f"{row['reward_currency']} "
        f"{row['reward_amount']}",
        f"- Probabilidade de pagamento: "
        f"{row['payment_probability']}%",
        f"- Valor esperado: "
        f"{row['expected_cash_value']}",
        f"- Valor/hora ajustado: "
        f"{row['adjusted_value_per_hour']}",
        f"- Readiness: "
        f"**{row['readiness_score']}**",
        f"- Status: "
        f"**{row['planning_status']}**",
        f"- Plano: `{row['plan_file']}`",
        f"- URL: {row['source_url']}",
        "",
    ])

REPORT_PATH.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print("===== EXECUTION PLANNER SUMMARY =====")
print(
    "Plans created:",
    len(created_plans),
)
print(
    "Ready for human approval:",
    counts.get(
        "ready_for_human_approval",
        0,
    ),
)
print(
    "Requirements review required:",
    counts.get(
        "requirements_review_required",
        0,
    ),
)
print(
    "Not ready:",
    counts.get(
        "not_ready",
        0,
    ),
)
print(
    "Blocked safety review:",
    counts.get(
        "blocked_safety_review",
        0,
    ),
)

print()
print("===== EXECUTION PLANS CREATED =====")

if created_plans:
    for index, plan in enumerate(
        created_plans,
        1,
    ):
        print()
        print(
            f"{index}. {plan['title']}"
        )
        print(
            "   requester:",
            plan["organization"],
        )
        print(
            "   repository:",
            plan["repository"],
        )
        print(
            "   issue:",
            plan["issue_number"],
        )
        print(
            "   reward:",
            plan["reward_currency"],
            plan["reward_amount"],
        )
        print(
            "   payment probability:",
            f"{plan['payment_probability']}%",
        )
        print(
            "   expected cash value:",
            plan["expected_cash_value"],
        )
        print(
            "   value/hour:",
            plan["adjusted_value_per_hour"],
        )
        print(
            "   readiness:",
            plan["readiness_score"],
        )
        print(
            "   status:",
            plan["planning_status"],
        )
        print(
            "   plan file:",
            plan["plan_file"],
        )
        print(
            "   url:",
            plan["url"],
        )
else:
    print(
        "Nenhuma nova oportunidade atingiu "
        "o gate mínimo para planejamento."
    )

conn.close()
