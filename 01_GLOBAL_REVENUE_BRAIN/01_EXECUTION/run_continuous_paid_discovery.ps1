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

$Runner = Join-Path 
    $ProjectRoot 
    "01_EXECUTION\run_continuous_paid_discovery.py"

Set-Location $ProjectRoot

& $Python $Runner

exit $LASTEXITCODE
