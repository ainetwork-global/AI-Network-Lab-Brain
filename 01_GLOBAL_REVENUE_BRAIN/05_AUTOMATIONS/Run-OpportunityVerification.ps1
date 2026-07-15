param(
    [int]$Limit = 30,
    [int]$Timeout = 20,
    [double]$Delay = 0.5,
    [switch]$OpenReport
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$PythonExecutable = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$EngineFile = Join-Path $ProjectRoot "03_INTELLIGENCE\opportunity_verification_engine.py"
$ReportFile = Join-Path $ProjectRoot "12_REPORTS\LATEST_VERIFIED_OPPORTUNITIES.md"

if (-not (Test-Path $PythonExecutable)) {
    throw "Python do ambiente virtual não encontrado: $PythonExecutable"
}

if (-not (Test-Path $EngineFile)) {
    throw "Verification Engine não encontrado: $EngineFile"
}

Set-Location $ProjectRoot

& $PythonExecutable $EngineFile `
    --limit $Limit `
    --timeout $Timeout `
    --delay $Delay

$EngineExitCode = $LASTEXITCODE

if ($EngineExitCode -notin @(0, 2)) {
    throw "Verification Engine terminou com código: $EngineExitCode"
}

if (Test-Path $ReportFile) {
    Write-Host ""
    Write-Host "Relatório gerado:" -ForegroundColor Green
    Write-Host $ReportFile

    if ($OpenReport) {
        Invoke-Item $ReportFile
    }
}
else {
    Write-Warning "O relatório ainda não foi gerado."
}
