$ErrorActionPreference = "Stop"

$BrainRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$Engine = Join-Path $BrainRoot "03_INTELLIGENCE\payment_confidence_engine.py"
$Handoff = Join-Path $BrainRoot "01_GLOBAL_REVENUE_BRAIN\05_EXECUTION\NEXT_PAYMENT_EXECUTION.json"
$RejectFile = Join-Path $BrainRoot "01_GLOBAL_REVENUE_BRAIN\06_REJECTIONS\payment_false_positives.csv"
$CurrentTarget = Join-Path $BrainRoot "01_GLOBAL_REVENUE_BRAIN\00_CURRENT_STATE\CURRENT_BEST_TARGET.md"
$ReportFile = Join-Path $BrainRoot "01_GLOBAL_REVENUE_BRAIN\12_REPORTS\LATEST_LIVE_CANDIDATE_PREFLIGHT.md"
$WorkspaceRoot = Join-Path $env:USERPROFILE "Global-Revenue-Execution"

New-Item -ItemType Directory -Force (Split-Path $RejectFile -Parent) | Out-Null
New-Item -ItemType Directory -Force (Split-Path $ReportFile -Parent) | Out-Null
New-Item -ItemType Directory -Force $WorkspaceRoot | Out-Null

function Invoke-Engine {
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
        throw "Payment Confidence Engine terminou com erro."
    }
}

function Add-Rejection {
    param(
        [string]$Repository,
        [string]$IssueNumber,
        [string]$Score,
        [string]$Code,
        [string]$Reason,
        [string]$Evidence
    )

    $Existing = @()

    if (Test-Path $RejectFile) {
        $Existing = @(Import-Csv $RejectFile)
    }

    $Exists = @(
        $Existing | Where-Object {
            $_.repository -eq $Repository -and
            [string]$_.issue_number -eq [string]$IssueNumber
        }
    ).Count -gt 0

    if (-not $Exists) {
        $Record = [PSCustomObject]@{
            rejected_at      = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            repository       = $Repository
            issue_number     = $IssueNumber
            prior_score      = $Score
            rejection_code   = $Code
            rejection_reason = $Reason
            evidence         = $Evidence
        }

        if (Test-Path $RejectFile) {
            $Record | Export-Csv $RejectFile -Append -NoTypeInformation -Encoding UTF8
        }
        else {
            $Record | Export-Csv $RejectFile -NoTypeInformation -Encoding UTF8
        }
    }

    if (Test-Path $Handoff) {
        Remove-Item $Handoff -Force
    }

    $Lines = @(
        "# Current Best Target",
        "",
        "Status: REJECTED_BY_LIVE_PREFLIGHT",
        "",
        "- Repository: $Repository",
        "- Issue: $IssueNumber",
        "- Previous confidence: $Score",
        "- Rejection code: $Code",
        "",
        "## Reason",
        "",
        $Reason,
        "",
        "## Evidence",
        "",
        $Evidence
    )

    $Lines | Set-Content $CurrentTarget -Encoding UTF8
}

for ($Attempt = 1; $Attempt -le 15; $Attempt++) {

    Write-Host ""
    Write-Host "==============================================" -ForegroundColor DarkCyan
    Write-Host "SELEÇÃO $Attempt DE 15" -ForegroundColor DarkCyan
    Write-Host "==============================================" -ForegroundColor DarkCyan

    Invoke-Engine

    if (-not (Test-Path $Handoff)) {
        Write-Host ""
        Write-Host "Nenhum candidato atingiu o limiar." -ForegroundColor Yellow
        exit 0
    }

    $Target = Get-Content $Handoff -Raw | ConvertFrom-Json

    $Repository = [string]$Target.repository
    $IssueNumber = [string]$Target.issue_number
    $Confidence = [string]$Target.payment_confidence_score

    Write-Host ""
    Write-Host "===== LIVE PREFLIGHT =====" -ForegroundColor Cyan
    Write-Host "Repository : $Repository"
    Write-Host "Issue      : $IssueNumber"
    Write-Host "Confidence : $Confidence"

    $IssueJson = gh issue view $IssueNumber `
        --repo $Repository `
        --json number,title,body,state,url,comments 2>$null

    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($IssueJson)) {
        Add-Rejection `
            -Repository $Repository `
            -IssueNumber $IssueNumber `
            -Score $Confidence `
            -Code "LIVE_LOOKUP_FAILED" `
            -Reason "Não foi possível confirmar a issue ao vivo." `
            -Evidence "gh issue view falhou."

        continue
    }

    $Issue = $IssueJson | ConvertFrom-Json
    $Comments = @($Issue.comments)

    $CommentText = (
        $Comments | ForEach-Object {
            [string]$_.body
        }
    ) -join "`n"

    $AllText = @(
        [string]$Issue.title
        [string]$Issue.body
        $CommentText
    ) -join "`n"

    $PrNumbers = [System.Collections.Generic.HashSet[string]]::new()

    foreach ($Match in [regex]::Matches(
        $CommentText,
        "(?i)github\.com/[^/\s]+/[^/\s]+/pull/([0-9]+)"
    )) {
        [void]$PrNumbers.Add($Match.Groups[1].Value)
    }

    foreach ($Match in [regex]::Matches(
        $CommentText,
        "(?i)\bPR\s*#?\s*([0-9]+)\b"
    )) {
        [void]$PrNumbers.Add($Match.Groups[1].Value)
    }

    $AttemptComments = @(
        $Comments | Where-Object {
            [string]$_.body -match "(?i)/attempt|/claim|working on|submitted|pull request|security PR|my submission"
        }
    )

    $ExplicitReward = (
        $AllText -match "(?is)(bounty|reward|payout).{0,120}(USD|USDC|USDT|\$|EUR|€)\s*[0-9]"
    ) -or (
        $AllText -match "(?is)(USD|USDC|USDT|\$|EUR|€)\s*[0-9][0-9,.]*.{0,120}(bounty|reward|payout)"
    )

    $PrCount = $PrNumbers.Count
    $AttemptCount = $AttemptComments.Count
    $CommentCount = $Comments.Count

    $CompetitionScore = 0
    $CompetitionScore += [Math]::Min(60, $PrCount * 12)
    $CompetitionScore += [Math]::Min(40, $AttemptCount * 8)

    if ($CompetitionScore -ge 50) {
        $CompetitionLevel = "SATURATED"
    }
    elseif ($CompetitionScore -ge 25) {
        $CompetitionLevel = "HIGH"
    }
    elseif ($CompetitionScore -ge 10) {
        $CompetitionLevel = "MODERATE"
    }
    else {
        $CompetitionLevel = "LOW"
    }

    Write-Host "Issue aberta       : $($Issue.state)"
    Write-Host "Reward explícito   : $ExplicitReward"
    Write-Host "Comentários        : $CommentCount"
    Write-Host "Tentativas         : $AttemptCount"
    Write-Host "PRs mencionados    : $PrCount"
    Write-Host "Competition score  : $CompetitionScore"
    Write-Host "Competition level  : $CompetitionLevel"

    $ReportLines = @(
        "# Latest Live Candidate Preflight",
        "",
        "- Checked at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
        "- Repository: $Repository",
        "- Issue: $IssueNumber",
        "- Title: $($Issue.title)",
        "- State: $($Issue.state)",
        "- Payment confidence: $Confidence",
        "- Explicit reward: $ExplicitReward",
        "",
        "## Competition",
        "",
        "- Comments: $CommentCount",
        "- Attempt comments: $AttemptCount",
        "- Unique PR references: $PrCount",
        "- Competition score: $CompetitionScore",
        "- Competition level: $CompetitionLevel"
    )

    $ReportLines | Set-Content $ReportFile -Encoding UTF8

    if ([string]$Issue.state -ne "OPEN") {
        Add-Rejection `
            -Repository $Repository `
            -IssueNumber $IssueNumber `
            -Score $Confidence `
            -Code "ISSUE_NOT_OPEN" `
            -Reason "A issue não está aberta." `
            -Evidence "GitHub state: $($Issue.state)"

        continue
    }

    if (-not $ExplicitReward) {
        Add-Rejection `
            -Repository $Repository `
            -IssueNumber $IssueNumber `
            -Score $Confidence `
            -Code "REWARD_NOT_CONFIRMED_LIVE" `
            -Reason "A leitura ao vivo não confirmou recompensa ao executor." `
            -Evidence "Valor e linguagem de bounty não estavam claramente conectados."

        continue
    }

    if (
        $CompetitionLevel -ne "LOW" -or
        $PrCount -ge 2 -or
        $AttemptCount -ge 2
    ) {
        Add-Rejection `
            -Repository $Repository `
            -IssueNumber $IssueNumber `
            -Score $Confidence `
            -Code "COMPETITION_ABOVE_LOW" `
            -Reason "Somente oportunidades com concorrência LOW podem iniciar execução." `
            -Evidence "comments=$CommentCount; attempts=$AttemptCount; pr_references=$PrCount; score=$CompetitionScore"

        Write-Host ""
        Write-Host "Candidato rejeitado. Selecionando o próximo..." -ForegroundColor Yellow
        continue
    }

    Write-Host ""
    Write-Host "===== CANDIDATO APROVADO NO LIVE PREFLIGHT =====" -ForegroundColor Green

    $SafeName = $Repository -replace "[^a-zA-Z0-9._-]", "_"
    $Workspace = Join-Path $WorkspaceRoot $SafeName

    if (-not (Test-Path $Workspace)) {
        gh repo clone $Repository $Workspace

        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao clonar o candidato aprovado."
        }
    }

    gh issue view $IssueNumber `
        --repo $Repository `
        --comments |
        Set-Content `
            (Join-Path $Workspace "PAYMENT_TARGET_ISSUE.md") `
            -Encoding UTF8

    $PlanLines = @(
        "# Payment Target Execution Start",
        "",
        "- Repository: $Repository",
        "- Issue: $IssueNumber",
        "- Reward USD: $($Target.reward_usd)",
        "- Payment confidence: $Confidence",
        "- Competition: $CompetitionLevel",
        "- Workspace: $Workspace",
        "",
        "Status: LIVE_PREFLIGHT_PASSED",
        "",
        "Nenhum comentário, claim, push ou pull request foi realizado."
    )

    $PlanLines |
        Set-Content `
            (Join-Path $Workspace "EXECUTION_START.md") `
            -Encoding UTF8

    Write-Host ""
    Write-Host "===== EXECUÇÃO LOCAL AUTORIZADA =====" -ForegroundColor Green
    Write-Host "Repository : $Repository"
    Write-Host "Issue      : $IssueNumber"
    Write-Host "Workspace  : $Workspace"
    Write-Host "Competition: $CompetitionLevel"

    exit 0
}

throw "Foram analisados 15 candidatos sem encontrar oportunidade elegível."

