import re
import sys
from pathlib import Path


if len(sys.argv) != 2:
    raise SystemExit(
        "Uso: repair_revenue_pipeline_worker_state.py "
        "<run_global_revenue_pipeline.ps1>"
    )


path = Path(sys.argv[1]).resolve()

if not path.exists():
    raise SystemExit(f"Arquivo não encontrado: {path}")


content = path.read_text(
    encoding="utf-8-sig",
)


throw_messages = [
    "O Worker não retornou um estado reconhecido.",
    "O Worker não recebeu um alvo READY_TO_EXECUTE.",
]


throw_position = -1

for message in throw_messages:
    position = content.find(message)

    if position >= 0:
        throw_position = position
        break


if throw_position < 0:
    raise SystemExit(
        "Não foi encontrada a validação antiga do Worker."
    )


def find_enclosing_if_block(text, position):
    candidates = [
        match.start()
        for match in re.finditer(
            r"(?m)^[ \t]*if\s*\(",
            text[:position],
        )
    ]

    for start in reversed(candidates):
        open_brace = text.find("{", start)

        if open_brace < 0 or open_brace > position:
            continue

        depth = 0
        in_single = False
        in_double = False
        escape = False

        for index in range(open_brace, len(text)):
            char = text[index]

            if escape:
                escape = False
                continue

            if char == "`":
                escape = True
                continue

            if char == "'" and not in_double:
                in_single = not in_single
                continue

            if char == '"' and not in_single:
                in_double = not in_double
                continue

            if in_single or in_double:
                continue

            if char == "{":
                depth += 1

            elif char == "}":
                depth -= 1

                if depth == 0:
                    if start <= position <= index:
                        return start, index + 1

                    break

    return None


block = find_enclosing_if_block(
    content,
    throw_position,
)

if not block:
    raise SystemExit(
        "Não foi possível localizar o bloco IF "
        "que contém a validação antiga."
    )


block_start, block_end = block


validation_block = r'''
# ================================================================
# WORKER STATE VALIDATION
# ================================================================

$WorkerResultFile = Join-Path `
    $BrainRoot `
    "07_REVENUE_WORKER\NEXT_EXECUTION.md"

if (-not (Test-Path $WorkerResultFile)) {
    throw "NEXT_EXECUTION.md não foi produzido pelo Worker."
}

$WorkerContent = Get-Content `
    $WorkerResultFile `
    -Raw `
    -Encoding UTF8

if ([string]::IsNullOrWhiteSpace($WorkerContent)) {
    throw "NEXT_EXECUTION.md foi produzido vazio."
}

$WorkerState = ""

if ($WorkerContent -match "(?m)^Worker decision:\s*READY_TO_BEGIN\s*$") {
    $WorkerState = "READY_TO_BEGIN"
}
elseif ($WorkerContent -match "(?m)^Execution status:\s*READY_TO_EXECUTE\s*$") {
    $WorkerState = "READY_TO_EXECUTE"
}
elseif ($WorkerContent -match "(?m)^Worker decision:\s*AWAITING_HUMAN_APPROVAL\s*$") {
    $WorkerState = "AWAITING_HUMAN_APPROVAL"
}
elseif ($WorkerContent -match "(?m)^Execution status:\s*NO_ACTIONABLE_CANDIDATE\s*$") {
    $WorkerState = "NO_ACTIONABLE_CANDIDATE"
}
elseif ($WorkerContent -match "(?m)^Result:\s*NO_ACTIONABLE_CANDIDATE\s*$") {
    $WorkerState = "NO_ACTIONABLE_CANDIDATE"
}

switch ($WorkerState) {
    "READY_TO_BEGIN" {
        Write-Host `
            "Worker encontrou uma oportunidade pronta para início." `
            -ForegroundColor Green
    }

    "READY_TO_EXECUTE" {
        Write-Host `
            "Worker encontrou uma oportunidade pronta para execução." `
            -ForegroundColor Green
    }

    "AWAITING_HUMAN_APPROVAL" {
        Write-Host `
            "Worker encontrou uma oportunidade aguardando aprovação humana." `
            -ForegroundColor Yellow
    }

    "NO_ACTIONABLE_CANDIDATE" {
        Write-Host `
            "Worker concluiu o ciclo sem candidato executável." `
            -ForegroundColor Yellow

        Write-Host `
            "Isso é um resultado válido e não representa falha." `
            -ForegroundColor DarkYellow
    }

    default {
        Write-Host ""
        Write-Host "Conteúdo recebido do Worker:" `
            -ForegroundColor Yellow

        Write-Host $WorkerContent

        throw "O Worker retornou um estado inválido ou desconhecido."
    }
}

Write-Host "Estado final do Worker: $WorkerState" `
    -ForegroundColor Cyan
'''.strip("\n")


updated = (
    content[:block_start]
    + validation_block
    + content[block_end:]
)


# Remove normalizações antigas e duplicadas imediatamente anteriores
# ao novo bloco, caso tenham sobrado de tentativas anteriores.
updated = re.sub(
    r'''(?ms)
^[ \t]*\#\s*Normaliza\s+o\s+conteúdo\s+do\s+Worker.*?
^[ \t]*\$WorkerContent\s*=\s*@\(\$WorkerContent\)\s*-join\s*\[Environment\]::NewLine\s*
''',
    "",
    updated,
)


path.write_text(
    updated,
    encoding="utf-8",
)


print("=" * 72)
print("REVENUE PIPELINE WORKER STATE REPAIR")
print("=" * 72)
print("Arquivo:", path)
print("Bloco antigo removido:", block_start, block_end)
print("Validação limpa instalada.")
print()
print("Estados válidos:")
print("- READY_TO_BEGIN")
print("- READY_TO_EXECUTE")
print("- AWAITING_HUMAN_APPROVAL")
print("- NO_ACTIONABLE_CANDIDATE")
