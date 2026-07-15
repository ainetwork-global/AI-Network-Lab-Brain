param(
    [switch]$OpenReport
)

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$Pipeline = Join-Path $ProjectRoot "10_SCRIPTS\run_revenue_pipeline.py"
$Report = Join-Path $ProjectRoot "12_REPORTS\LATEST_REVENUE_OPPORTUNITIES.md"

if (-not (Test-Path $Python)) {
    Write-Host "Ambiente Python não encontrado: $Python" -ForegroundColor Red
    return
}

& $Python $Pipeline

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "GLOBAL REVENUE HUNTER CONCLUÍDO" -ForegroundColor Green
    Write-Host "Relatório: $Report" -ForegroundColor Cyan

    if ($OpenReport -and (Test-Path $Report)) {
        Start-Process notepad.exe $Report
    }
}
else {
    Write-Host ""
    Write-Host "O pipeline terminou com erro." -ForegroundColor Red
}
