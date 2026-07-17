$ErrorActionPreference = "Stop"

$ProjectRoot = Join-Path 
    $env:USERPROFILE 
    "AI-Network-Lab-Brain\01_GLOBAL_REVENUE_BRAIN"

$Python = Join-Path 
    $ProjectRoot 
    ".venv\Scripts\python.exe"

$LearningEngine = Join-Path 
    $ProjectRoot 
    "06_LEARNING\revenue_learning_engine.py"

Set-Location $ProjectRoot

& $Python $LearningEngine

exit $LASTEXITCODE
