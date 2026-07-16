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

$RankingScript = Join-Path 
    $ProjectRoot 
    "03_INTELLIGENCE\execution_candidate_ranking.py"

Set-Location $ProjectRoot

& $Python $RankingScript

exit $LASTEXITCODE
