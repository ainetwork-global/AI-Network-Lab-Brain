$ErrorActionPreference = "Stop"

$ProjectRoot = Join-Path 
    $env:USERPROFILE 
    "AI-Network-Lab-Brain\01_GLOBAL_REVENUE_BRAIN"

$Python = Join-Path 
    $ProjectRoot 
    ".venv\Scripts\python.exe"

$Engine = Join-Path 
    $ProjectRoot 
    "05_SETTLEMENT\execution_result_engine.py"

Set-Location $ProjectRoot

& $Python $Engine

exit $LASTEXITCODE
