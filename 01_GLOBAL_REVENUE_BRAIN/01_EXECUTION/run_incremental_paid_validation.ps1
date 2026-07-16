$ErrorActionPreference = "Stop"

$BrainRoot = Join-Path 
    $env:USERPROFILE 
    "AI-Network-Lab-Brain"

$ProjectRoot = Join-Path 
    $BrainRoot 
    "01_GLOBAL_REVENUE_BRAIN"

$Python = Join-Path 
    $ProjectRoot 
    ".venv\Scripts\python.exe"

$Validator = Join-Path 
    $ProjectRoot 
    "03_INTELLIGENCE\incremental_paid_task_truth_gate.py"

Set-Location $ProjectRoot

& $Python $Validator

exit $LASTEXITCODE
