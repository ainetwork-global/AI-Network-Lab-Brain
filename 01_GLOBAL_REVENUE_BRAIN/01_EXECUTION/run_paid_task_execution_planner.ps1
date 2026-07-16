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

$Planner = Join-Path 
    $ProjectRoot 
    "01_EXECUTION\build_paid_task_execution_plans.py"

Set-Location $ProjectRoot

& $Python $Planner

exit $LASTEXITCODE
