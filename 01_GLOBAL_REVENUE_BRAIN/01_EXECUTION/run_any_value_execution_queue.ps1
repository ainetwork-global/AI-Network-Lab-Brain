param(
    [string]$BrainRoot = "C:\Users\AP10\AI-Network-Lab-Brain"
)

$ErrorActionPreference = "Stop"

$GlobalBrain = Join-Path `
    $BrainRoot `
    "01_GLOBAL_REVENUE_BRAIN"

$SelectorPath = Join-Path `
    $GlobalBrain `
    "01_EXECUTION\build_any_value_execution_queue.py"

if (-not (Test-Path $SelectorPath)) {
    throw "Selector não encontrado: $SelectorPath"
}

$VenvPython = Join-Path `
    $GlobalBrain `
    ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    & $VenvPython $SelectorPath $GlobalBrain
    exit $LASTEXITCODE
}

if (Get-Command python -ErrorAction SilentlyContinue) {
    & python $SelectorPath $GlobalBrain
    exit $LASTEXITCODE
}

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $SelectorPath $GlobalBrain
    exit $LASTEXITCODE
}

throw "Python não encontrado."
