$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Engine = Join-Path $Root "03_INTELLIGENCE\global_source_priority_engine.py"

Write-Host ""
Write-Host "===== GLOBAL REVENUE SOURCE ROUTER =====" `
    -ForegroundColor Cyan

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $Engine
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python $Engine
}
else {
    throw "Python não encontrado."
}

if ($LASTEXITCODE -ne 0) {
    throw "Global Source Priority Engine terminou com erro."
}
