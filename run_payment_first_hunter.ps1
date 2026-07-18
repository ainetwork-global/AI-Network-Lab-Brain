$ErrorActionPreference = "Stop"

$BrainRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$Engine = Join-Path $BrainRoot "03_INTELLIGENCE\payment_confidence_engine.py"
$Handoff = Join-Path $BrainRoot "01_GLOBAL_REVENUE_BRAIN\05_EXECUTION\NEXT_PAYMENT_EXECUTION.json"
$WorkspaceRoot = Join-Path $env:USERPROFILE "Global-Revenue-Execution"

Write-Host ""
Write-Host "===== PAYMENT-FIRST HUNTER =====" -ForegroundColor Cyan

if (Get-Command py -ErrorAction SilentlyContinue) {
    & py -3 $Engine
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    & python $Engine
}
else {
    throw "Python não foi encontrado."
}

if ($LASTEXITCODE -ne 0) {
    throw "Payment Confidence Engine falhou com código $LASTEXITCODE."
}

if (-not (Test-Path $Handoff)) {
    Write-Host ""
    Write-Host "Nenhum candidato atingiu o limiar de execução local." `
        -ForegroundColor Yellow
    exit 0
}

$Target = Get-Content $Handoff -Raw | ConvertFrom-Json

if (
    [string]::IsNullOrWhiteSpace($Target.repository) -or
    [string]::IsNullOrWhiteSpace($Target.issue_number)
) {
    Write-Host ""
    Write-Host "Candidato sem repositório ou issue. Execução não iniciada." `
        -ForegroundColor Yellow
    exit 0
}

New-Item -ItemType Directory -Force -Path $WorkspaceRoot | Out-Null

$SafeRepoName = ($Target.repository -replace '[^a-zA-Z0-9._-]', '_')
$TargetWorkspace = Join-Path $WorkspaceRoot $SafeRepoName
$IssueFile = Join-Path $TargetWorkspace "PAYMENT_TARGET_ISSUE.md"
$PlanFile = Join-Path $TargetWorkspace "EXECUTION_START.md"

Write-Host ""
Write-Host "===== CANDIDATO FORTE IDENTIFICADO =====" `
    -ForegroundColor Green

Write-Host "Repository : $($Target.repository)"
Write-Host "Issue      : $($Target.issue_number)"
Write-Host "Reward     : USD $($Target.reward_usd)"
Write-Host "Confidence : $($Target.payment_confidence_score)"

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    throw "GitHub CLI não foi encontrado."
}

& gh auth status
if ($LASTEXITCODE -ne 0) {
    throw "GitHub CLI não está autenticado."
}

if (-not (Test-Path $TargetWorkspace)) {
    Write-Host ""
    Write-Host "Clonando repositório..." -ForegroundColor Cyan

    & gh repo clone $Target.repository $TargetWorkspace

    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível clonar $($Target.repository)."
    }
}
else {
    Write-Host ""
    Write-Host "Workspace já existe: $TargetWorkspace" `
        -ForegroundColor Yellow
}

Push-Location $TargetWorkspace

try {
    & gh issue view $Target.issue_number `
        --repo $Target.repository `
        --comments | Set-Content $IssueFile -Encoding UTF8

    @"
# Payment Target Execution Start

- Repository: $($Target.repository)
- Issue: $($Target.issue_number)
- Reward USD: $($Target.reward_usd)
- Payment confidence: $($Target.payment_confidence_score)
- Estimated hours: $($Target.estimated_hours)
- Source URL: $($Target.url)
- Started locally at: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

## Execution state

`LOCAL_REPOSITORY_CLONED`

`ISSUE_CAPTURED_FOR_TECHNICAL_ANALYSIS`

## Positive payment evidence

$($Target.positive_evidence)

## Known risks

$($Target.risk_evidence)

## Next operation

1. Read repository contribution rules.
2. Reproduce or validate the requested task.
3. Map affected files and tests.
4. Produce an implementation plan.
5. Begin implementation only after technical feasibility is confirmed.

No public claim, issue comment, branch push, pull request, payment request
or external commitment was performed by this local initialization stage.
"@ | Set-Content $PlanFile -Encoding UTF8

    Write-Host ""
    Write-Host "===== EXECUÇÃO LOCAL INICIADA =====" `
        -ForegroundColor Green

    Write-Host "Workspace:"
    Write-Host $TargetWorkspace

    Write-Host ""
    Write-Host "Issue capturada:"
    Write-Host $IssueFile

    Write-Host ""
    Write-Host "Plano inicial:"
    Write-Host $PlanFile

    Write-Host ""
    Write-Host "===== STATUS DO REPOSITÓRIO =====" `
        -ForegroundColor Yellow

    git status --short
}
finally {
    Pop-Location
}
