param(
    [string]$BrainRoot = "C:\Users\AP10\AI-Network-Lab-Brain"
)

$ErrorActionPreference = "Stop"

$GlobalBrain = Join-Path $BrainRoot "01_GLOBAL_REVENUE_BRAIN"
$ScriptPath = Join-Path `
    $GlobalBrain `
    "03_SOURCE_INTELLIGENCE\source_intelligence.py"

if (-not (Test-Path $ScriptPath)) {
    throw "Source Intelligence não encontrado: $ScriptPath"
}

$VenvPython = Join-Path $GlobalBrain ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    & $VenvPython `
        $ScriptPath `
        --global-brain $GlobalBrain

    exit $LASTEXITCODE
}

$PythonCommand = Get-Command python -ErrorAction SilentlyContinue

if ($PythonCommand) {
    & python `
        $ScriptPath `
        --global-brain $GlobalBrain

    exit $LASTEXITCODE
}

$PyCommand = Get-Command py -ErrorAction SilentlyContinue

if ($PyCommand) {
    & py -3 `
        $ScriptPath `
        --global-brain $GlobalBrain

    exit $LASTEXITCODE
}

throw "Python não encontrado."
