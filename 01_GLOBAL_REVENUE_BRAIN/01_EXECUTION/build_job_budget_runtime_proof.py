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

VALIDATOR_FILE = (
    REPOSITORY
    / "apps"
    / "api"
    / "src"
    / "validators"
    / "job.js"
)

PROOF_WORKSPACE = (
    Path.home()
    / "Revenue-Workspaces"
    / "SecureBananaLabs-bug-bounty-743"
    / "proof"
    / "job-budget-range"
)

RUNNER_FILE = (
    PROOF_WORKSPACE
    / "runtime-proof-runner.mjs"
)

STATE_FILE = (
    ROOT
    / "00_CURRENT_STATE"
    / "SECUREBANANA_JOB_BUDGET_RUNTIME_PROOF.json"
)

REPORT_FILE = (
    ROOT
    / "12_REPORTS"
    / "LATEST_SECUREBANANA_JOB_BUDGET_RUNTIME_PROOF.md"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def run_command(
    command: list[str],
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
            "stdout": (process.stdout or "")[-30000:],
            "stderr": (process.stderr or "")[-30000:],
            "timed_out": False,
        }

    except subprocess.TimeoutExpired as error:
        return {
            "command": command,
            "return_code": None,
            "stdout": str(error.stdout or "")[-30000:],
            "stderr": str(error.stderr or "")[-30000:],
            "timed_out": True,
        }


def find_package_root(
    start: Path,
) -> Path | None:
    current = start.parent

    while current != current.parent:
        if (current / "package.json").exists():
            return current

        if current == REPOSITORY:
            break

        current = current.parent

    return None


def find_node_modules(
    start: Path,
) -> Path | None:
    current = start

    while current != current.parent:
        candidate = current / "node_modules"

        if candidate.exists():
            return candidate

        if current == REPOSITORY:
            break

        current = current.parent

    repository_node_modules = (
        REPOSITORY
        / "node_modules"
    )

    if repository_node_modules.exists():
        return repository_node_modules

    return None


if not VALIDATOR_FILE.exists():
    raise RuntimeError(
        f"Validator não encontrado: {VALIDATOR_FILE}"
    )

node = shutil.which("node")

if not node:
    raise RuntimeError(
        "Node.js não foi encontrado no PATH."
    )

source = VALIDATOR_FILE.read_text(
    encoding="utf-8",
    errors="ignore",
)

package_root = find_package_root(
    VALIDATOR_FILE
)

node_modules = find_node_modules(
    VALIDATOR_FILE.parent
)

has_budget_min = bool(
    re.search(
        r"\bbudgetMin\b",
        source,
        re.IGNORECASE,
    )
)

has_budget_max = bool(
    re.search(
        r"\bbudgetMax\b",
        source,
        re.IGNORECASE,
    )
)

has_cross_field_validation = bool(
    re.search(
        (
            r"\.refine\s*\("
            r"|\.superRefine\s*\("
            r"|budgetMin\s*<=\s*budgetMax"
            r"|budgetMax\s*>=\s*budgetMin"
        ),
        source,
        re.IGNORECASE,
    )
)

PROOF_WORKSPACE.mkdir(
    parents=True,
    exist_ok=True,
)

validator_url = VALIDATOR_FILE.resolve().as_uri()

runner_source = f'''
import {{ pathToFileURL }} from "node:url";

const validatorUrl = {json.dumps(validator_url)};

const output = {{
  validator_url: validatorUrl,
  module_loaded: false,
  export_names: [],
  schemas_tested: [],
  confirmed_bug: false,
  invalid_range_accepted: false,
  valid_range_accepted: false,
  runtime_status: "not_started",
  error: null
}};

function looksLikeSchema(value) {{
  return Boolean(
    value &&
    typeof value === "object" &&
    (
      typeof value.safeParse === "function" ||
      typeof value.parse === "function"
    )
  );
}}

function buildPayloadCandidates() {{
  return [
    {{
      title: "Runtime proof job",
      description: "Runtime proof for invalid budget range",
      budgetMin: 1000,
      budgetMax: 100
    }},
    {{
      title: "Runtime proof job",
      description: "Runtime proof for invalid budget range",
      budgetMin: 1000,
      budgetMax: 100,
      category: "development"
    }},
    {{
      title: "Runtime proof job",
      description: "Runtime proof for invalid budget range",
      budgetMin: 1000,
      budgetMax: 100,
      skills: ["javascript"]
    }},
    {{
      title: "Runtime proof job",
      description: "Runtime proof for invalid budget range",
      budgetMin: 1000,
      budgetMax: 100,
      category: "development",
      skills: ["javascript"]
    }}
  ];
}}

function buildValidPayload(invalidPayload) {{
  return {{
    ...invalidPayload,
    budgetMin: 100,
    budgetMax: 1000
  }};
}}

function evaluateSchema(schema, exportName) {{
  const invalidPayloads = buildPayloadCandidates();

  for (const invalidPayload of invalidPayloads) {{
    const validPayload = buildValidPayload(invalidPayload);

    let invalidResult;
    let validResult;

    try {{
      if (typeof schema.safeParse === "function") {{
        invalidResult = schema.safeParse(invalidPayload);
        validResult = schema.safeParse(validPayload);

        const invalidAccepted = Boolean(invalidResult?.success);
        const validAccepted = Boolean(validResult?.success);

        output.schemas_tested.push({{
          export_name: exportName,
          method: "safeParse",
          invalid_payload: invalidPayload,
          invalid_accepted: invalidAccepted,
          invalid_error:
            invalidResult?.error?.issues ??
            invalidResult?.error?.errors ??
            null,
          valid_payload: validPayload,
          valid_accepted: validAccepted,
          valid_error:
            validResult?.error?.issues ??
            validResult?.error?.errors ??
            null
        }});

        if (invalidAccepted) {{
          output.invalid_range_accepted = true;
        }}

        if (validAccepted) {{
          output.valid_range_accepted = true;
        }}

        if (invalidAccepted && validAccepted) {{
          output.confirmed_bug = true;
          return true;
        }}

      }} else if (typeof schema.parse === "function") {{
        let invalidAccepted = false;
        let validAccepted = false;
        let invalidError = null;
        let validError = null;

        try {{
          schema.parse(invalidPayload);
          invalidAccepted = true;
        }} catch (error) {{
          invalidError =
            error?.issues ??
            error?.errors ??
            String(error);
        }}

        try {{
          schema.parse(validPayload);
          validAccepted = true;
        }} catch (error) {{
          validError =
            error?.issues ??
            error?.errors ??
            String(error);
        }}

        output.schemas_tested.push({{
          export_name: exportName,
          method: "parse",
          invalid_payload: invalidPayload,
          invalid_accepted: invalidAccepted,
          invalid_error: invalidError,
          valid_payload: validPayload,
          valid_accepted: validAccepted,
          valid_error: validError
        }});

        if (invalidAccepted) {{
          output.invalid_range_accepted = true;
        }}

        if (validAccepted) {{
          output.valid_range_accepted = true;
        }}

        if (invalidAccepted && validAccepted) {{
          output.confirmed_bug = true;
          return true;
        }}
      }}
    }} catch (error) {{
      output.schemas_tested.push({{
        export_name: exportName,
        method: "unknown",
        runtime_error: String(error)
      }});
    }}
  }}

  return false;
}}

try {{
  const module = await import(validatorUrl);

  output.module_loaded = true;
  output.export_names = Object.keys(module);

  const candidates = [];

  for (const [name, value] of Object.entries(module)) {{
    if (looksLikeSchema(value)) {{
      candidates.push([name, value]);
    }}

    if (
      value &&
      typeof value === "object"
    ) {{
      for (const [childName, childValue] of Object.entries(value)) {{
        if (looksLikeSchema(childValue)) {{
          candidates.push([
            `${{name}}.${{childName}}`,
            childValue
          ]);
        }}
      }}
    }}
  }}

  if (looksLikeSchema(module.default)) {{
    candidates.push([
      "default",
      module.default
    ]);
  }}

  if (candidates.length === 0) {{
    output.runtime_status = "no_schema_export_detected";
  }} else {{
    output.runtime_status = "schemas_detected";

    for (const [name, schema] of candidates) {{
      if (evaluateSchema(schema, name)) {{
        break;
      }}
    }}

    if (output.confirmed_bug) {{
      output.runtime_status =
        "confirmed_invalid_budget_range_accepted";
    }} else if (
      output.invalid_range_accepted &&
      !output.valid_range_accepted
    ) {{
      output.runtime_status =
        "inconclusive_payload_shape";
    }} else if (
      !output.invalid_range_accepted &&
      output.valid_range_accepted
    ) {{
      output.runtime_status =
        "validation_rejects_invalid_range";
    }} else {{
      output.runtime_status =
        "inconclusive_no_payload_accepted";
    }}
  }}
}} catch (error) {{
  output.runtime_status = "module_load_failed";
  output.error = {{
    name: error?.name ?? null,
    message: error?.message ?? String(error),
    stack: error?.stack ?? null
  }};
}}

console.log(
  "PROOF_JSON_START"
);

console.log(
  JSON.stringify(
    output,
    null,
    2
  )
);

console.log(
  "PROOF_JSON_END"
);

process.exit(
  output.confirmed_bug
    ? 10
    : 0
);
'''

RUNNER_FILE.write_text(
    runner_source,
    encoding="utf-8",
)

environment_status = {
    "package_root": (
        str(package_root)
        if package_root
        else None
    ),
    "node_modules_found": bool(
        node_modules
    ),
    "node_modules_path": (
        str(node_modules)
        if node_modules
        else None
    ),
}

runtime_result = run_command(
    [
        node,
        str(RUNNER_FILE),
    ],
    cwd=(
        package_root
        if package_root
        else REPOSITORY
    ),
)

stdout = runtime_result["stdout"]

proof_match = re.search(
    (
        r"PROOF_JSON_START\s*"
        r"(\{.*\})\s*"
        r"PROOF_JSON_END"
    ),
    stdout,
    re.DOTALL,
)

runtime_proof: dict[str, Any] = {}

if proof_match:
    try:
        runtime_proof = json.loads(
            proof_match.group(1)
        )
    except json.JSONDecodeError:
        runtime_proof = {
            "runtime_status": (
                "invalid_proof_json"
            ),
            "raw_output": stdout,
        }
else:
    runtime_proof = {
        "runtime_status": (
            "proof_output_not_found"
        ),
        "raw_output": stdout,
    }

confirmed_bug = bool(
    runtime_proof.get(
        "confirmed_bug",
        False,
    )
)

module_loaded = bool(
    runtime_proof.get(
        "module_loaded",
        False,
    )
)

runtime_status = str(
    runtime_proof.get(
        "runtime_status",
        "unknown",
    )
)

if confirmed_bug:
    decision = (
        "RUNTIME_BUG_CONFIRMED"
    )

    confidence = 98.0

    recommended_next_action = (
        "check_duplicate_issues_before_preparing_fix"
    )

elif runtime_status == (
    "validation_rejects_invalid_range"
):
    decision = (
        "HYPOTHESIS_REJECTED"
    )

    confidence = 95.0

    recommended_next_action = (
        "discard_candidate_and_test_next_hypothesis"
    )

elif runtime_status == (
    "module_load_failed"
):
    decision = (
        "BLOCKED_MODULE_LOAD"
    )

    confidence = 35.0

    recommended_next_action = (
        "inspect_module_format_and_dependencies"
    )

elif runtime_status == (
    "no_schema_export_detected"
):
    decision = (
        "BLOCKED_SCHEMA_DISCOVERY"
    )

    confidence = 40.0

    recommended_next_action = (
        "inspect_validator_exports_and_create_targeted_loader"
    )

else:
    decision = (
        "INCONCLUSIVE_RUNTIME_PROOF"
    )

    confidence = 50.0

    recommended_next_action = (
        "inspect_required_payload_fields_and_retry_locally"
    )

state = {
    "generated_at": utc_now(),
    "repository": str(REPOSITORY),
    "validator_file": str(
        VALIDATOR_FILE
    ),
    "source_static_analysis": {
        "budget_min_present": has_budget_min,
        "budget_max_present": has_budget_max,
        "cross_field_validation_detected": (
            has_cross_field_validation
        ),
    },
    "environment": environment_status,
    "runtime_command": runtime_result,
    "runtime_proof": runtime_proof,
    "decision": decision,
    "confidence": confidence,
    "recommended_next_action": (
        recommended_next_action
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
    "# SecureBananaLabs — Job Budget Runtime Proof",
    "",
    f"Gerado em: {state['generated_at']}",
    "",
    "## Resultado",
    "",
    f"- Decisão: **{decision}**",
    f"- Confiança: **{confidence}**",
    f"- Runtime status: **{runtime_status}**",
    f"- Bug confirmado: **{'sim' if confirmed_bug else 'não'}**",
    (
        "- Próxima ação: "
        f"**{recommended_next_action}**"
    ),
    "",
    "## Hipótese",
    "",
    (
        "`budgetMin` maior que `budgetMax` pode ser "
        "aceito pelo validator de criação de jobs."
    ),
    "",
    "## Evidência estática",
    "",
    (
        "- `budgetMin` presente: "
        f"**{'sim' if has_budget_min else 'não'}**"
    ),
    (
        "- `budgetMax` presente: "
        f"**{'sim' if has_budget_max else 'não'}**"
    ),
    (
        "- Validação cruzada detectada: "
        f"**{'sim' if has_cross_field_validation else 'não'}**"
    ),
    "",
    "## Execução local",
    "",
    (
        "- Módulo carregado: "
        f"**{'sim' if module_loaded else 'não'}**"
    ),
    (
        "- `node_modules` encontrado: "
        f"**{'sim' if node_modules else 'não'}**"
    ),
    (
        "- Código-fonte alterado: **não**"
    ),
    (
        "- Dependências instaladas: **não**"
    ),
    (
        "- Publicação externa: **não**"
    ),
    "",
    "## Schemas testados",
    "",
]

schemas_tested = (
    runtime_proof.get(
        "schemas_tested",
        [],
    )
    or []
)

if not schemas_tested:
    lines.append(
        "- Nenhum schema foi executado."
    )

for index, schema in enumerate(
    schemas_tested,
    1,
):
    lines.extend([
        f"### Schema {index}",
        "",
        (
            "- Export: "
            f"`{schema.get('export_name')}`"
        ),
        (
            "- Método: "
            f"`{schema.get('method')}`"
        ),
        (
            "- Range inválido aceito: "
            f"**{schema.get('invalid_accepted')}**"
        ),
        (
            "- Range válido aceito: "
            f"**{schema.get('valid_accepted')}**"
        ),
        "",
    ])

if runtime_proof.get("error"):
    lines.extend([
        "## Erro de carregamento",
        "",
        "```text",
        json.dumps(
            runtime_proof["error"],
            ensure_ascii=False,
            indent=2,
        ),
        "```",
        "",
    ])

lines.extend([
    "## Segurança operacional",
    "",
    "- Código do repositório alterado: **não**",
    "- Instalação de dependências realizada: **não**",
    "- Issue criada: **não**",
    "- Comentário publicado: **não**",
    "- Fork criado: **não**",
    "- Pull request criado: **não**",
])

REPORT_FILE.write_text(
    "\n".join(lines),
    encoding="utf-8",
)

print()
print("===== TARGETED RUNTIME PROOF =====")
print("Validator:", VALIDATOR_FILE)
print("budgetMin present:", has_budget_min)
print("budgetMax present:", has_budget_max)
print(
    "Cross-field validation detected:",
    has_cross_field_validation,
)
print(
    "Node modules found:",
    bool(node_modules),
)
print(
    "Module loaded:",
    module_loaded,
)
print(
    "Schemas tested:",
    len(schemas_tested),
)

print()
print("===== RUNTIME PROOF RESULT =====")
print(
    "Runtime status:",
    runtime_status,
)
print(
    "Invalid range accepted:",
    runtime_proof.get(
        "invalid_range_accepted",
        False,
    ),
)
print(
    "Valid range accepted:",
    runtime_proof.get(
        "valid_range_accepted",
        False,
    ),
)
print(
    "Confirmed bug:",
    confirmed_bug,
)
print(
    "Decision:",
    decision,
)
print(
    "Confidence:",
    confidence,
)
print(
    "Recommended next action:",
    recommended_next_action,
)

if runtime_proof.get("error"):
    print()
    print("Module load error:")
    print(
        runtime_proof["error"].get(
            "message"
        )
    )

print()
print("===== RUNTIME PROOF SAFETY =====")
print("Source code modified: no")
print("Dependency install performed: no")
print("External publication performed: no")
print("Issue created: no")
print("Comment created: no")
print("Fork created: no")
print("Pull request created: no")
print("Report:", REPORT_FILE)
