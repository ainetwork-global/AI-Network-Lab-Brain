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

$Classifier = Join-Path 
    $ProjectRoot 
    "03_INTELLIGENCE\classify_payment_probability.py"

Set-Location $ProjectRoot

& $Python $Classifier

exit $LASTEXITCODE
