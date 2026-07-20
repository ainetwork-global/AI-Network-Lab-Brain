$ErrorActionPreference = "Stop"

$BrainRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$Engine = Join-Path `
    $BrainRoot `
    "03_INTELLIGENCE\payment_confidence_engine.py"

$Handoff = Join-Path `
    $BrainRoot `
    "01_GLOBAL_REVENUE_BRAIN\05_EXECUTION\NEXT_PAYMENT_EXECUTION.json"

$RejectFile = Join-Path `
    $BrainRoot `
    "01_GLOBAL_REVENUE_BRAIN\06_REJECTIONS\payment_false_positives.csv"

$CurrentTarget = Join-Path `
    $BrainRoot `
    "01_GLOBAL_REVENUE_BRAIN\00_CURRENT_STATE\CURRENT_BEST_TARGET.md"

$ValidationReport = Join-Path `
    $BrainRoot `
    "01_GLOBAL_REVENUE_BRAIN\12_REPORTS\LATEST_LIVE_CANDIDATE_PREFLIGHT.md"

$WorkspaceRoot = Join-Path `
    $env:USERPROFILE `
    "Global-Revenue-Execution"

$MaximumSelections = 15

function Invoke-PaymentEngine {
    Write-Host ""
    Write-Host "===== PAYMENT CONFIDENCE ENGINE =====" `
        -ForegroundColor Cyan

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
        throw "Payment Confidence Engine terminou com erro."
    }
}

function Add-LiveRejection {
    param(
        [Parameter(Mandatory)]
        [string]$Repository,

        [Parameter(Mandatory)]
        [string]$IssueNumber,

        [string]$PriorScore,

        [Parameter(Mandatory)]
        [string]$Code,

        [Parameter(Mandatory)]
        [string]$Reason,

        [string]$Evidence
    )

    $Existing = @()

    if (Test-Path $RejectFile) {
        $Existing = @(Import-Csv $RejectFile)
    }

    $AlreadyExists = @(
        $Existing | Where-Object {
            $_.repository -eq $Repository -and
            [string]$_.issue_number -eq [string]$IssueNumber
        }
    ).Count -gt 0

    if (-not $AlreadyExists) {
        [PSCustomObject]@{
            rejected_at      = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
            repository       = $Repository
            issue_number     = $IssueNumber
            prior_score      = $PriorScore
            rejection_code   = $Code
            rejection_reason = $Reason
            evidence         = $Evidence
        } | Export-Csv `
            $RejectFile `
            -Append `
            -NoTypeInformation `
            -Encoding UTF8
    }

    if (Test-Path $Handoff) {
        Remove-Item $Handoff -Force
    }

    @(
        "# Current Best Target"
        ""
        "Status: ``REJECTED_BY_LIVE_PREFLIGHT``"
        ""
        "- Repository: ``$Repository``"
        "- Issue: ``$IssueNumber``"
        "- Previous confidence: ``$PriorScore``"
        "- Rejection code: ``$Code``"
        ""
        "## Reason"
        ""
        $Reason
        ""
        "## Evidence"
        ""
        $Evidence
    ) | Set-Content $CurrentTarget -Encoding UTF8
}

function Get-UniquePullRequestReferences {
    param(
        [Parameter(Mandatory)]
        [string]$Text
    )

    $Numbers = [System.Collections.Generic.HashSet[string]]::new()

    $UrlMatches = [regex]::Matches(
        $Text,
        '(?i)github\.com/[^/\s]+/[^/\s]+/pull/([0-9]+)'
    )

    foreach ($Match in $UrlMatches) {
        [void]$Numbers.Add($Match.Groups[1].Value)
    }

    $PrMatches = [regex]::Matches(
        $Text,
        '(?i)\bPR\s*#?\s*([0-9]+)\b'
    )

    foreach ($Match in $PrMatches) {
        [void]$Numbers.Add($Match.Groups[1].Value)
    }

    return @($Numbers)
}

New-Item -ItemType Directory -Force $WorkspaceRoot | Out-Null

for ($SelectionAttempt = 1; $SelectionAttempt -le $MaximumSelections; $SelectionAttempt++) {

    Write-Host ""
    Write-Host "==============================================" `
        -ForegroundColor DarkCyan
    Write-Host "SELEÇÃO $SelectionAttempt DE $MaximumSelections" `
        -ForegroundColor DarkCyan
    Write-Host "==============================================" `
        -ForegroundColor DarkCyan

    Invoke-PaymentEngine

    if (-not (Test-Path $Handoff)) {
        Write-Host ""
        Write-Host "Nenhum candidato atingiu o limiar atual." `
            -ForegroundColor Yellow
        exit 0
    }

    $Target = Get-Content $Handoff -Raw | ConvertFrom-Json

    $Repository  = [string]$Target.repository
    $IssueNumber = [string]$Target.issue_number
    $Confidence  = [string]$Target.payment_confidence_score

    if (
        [string]::IsNullOrWhiteSpace($Repository) -or
        [string]::IsNullOrWhiteSpace($IssueNumber)
    ) {
        Add-LiveRejection `
            -Repository $Repository `
            -IssueNumber $IssueNumber `
            -PriorScore $Confidence `
            -Code "INVALID_TARGET_IDENTITY" `
            -Reason "O candidato não possui repositório e issue válidos." `
            -Evidence "Handoff incompleto."

        continue
    }

    Write-Host ""
    Write-Host "===== LIVE PREFLIGHT =====" -ForegroundColor Cyan
    Write-Host "Repository : $Repository"
    Write-Host "Issue      : $IssueNumber"
    Write-Host "Confidence : $Confidence"

    $IssueJson = gh issue view $IssueNumber `
        --repo $Repository `
        --json number,title,body,state,url,author,assignees,labels,comments,createdAt,updatedAt 2>$null

    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($IssueJson)) {
        Add-LiveRejection `
            -Repository $Repository `
            -IssueNumber $IssueNumber `
            -PriorScore $Confidence `
            -Code "LIVE_ISSUE_LOOKUP_FAILED" `
            -Reason "A issue não pôde ser confirmada diretamente no GitHub." `
            -Evidence "gh issue view terminou com erro."

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

    $PullRequestReferences = @(
        Get-UniquePullRequestReferences -Text $CommentText
    )

    $AttemptComments = @(
        $Comments | Where-Object {
            $_.body -match (
                '(?i)' +
                '/attempt|' +
                '/claim|' +
                'working on|' +
                'started working|' +
                'submitted (?:a |the )?(?:PR|pull request)|' +
                'I(?:''|’)ve submitted|' +
                'my submission|' +
                'security PRs? submitted|' +
                'claiming this'
            )
        }
    )

    $SubmissionComments = @(
        $Comments | Where-Object {
            $_.body -match (
                '(?i)' +
                'github\.com/.+?/pull/[0-9]+|' +
                '\bPR\s*#?\s*[0-9]+|' +
                'pull request'
            )
        }
    )

    $AllPrJson = gh pr list `
        --repo $Repository `
        --state all `
        --limit 200 `
        --json number,title,body,state,url,author 2>$null

    $RepositoryPRs = @()

    if (
        $LASTEXITCODE -eq 0 -and
        -not [string]::IsNullOrWhiteSpace($AllPrJson)
    ) {
        $RepositoryPRs = @($AllPrJson | ConvertFrom-Json)
    }

    $IssueUrlPattern = [regex]::Escape([string]$Issue.url)

    $DirectlyRelatedPRs = @(
        $RepositoryPRs | Where-Object {
            (
                [string]$_.body -match "(?i)(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*#?$IssueNumber\b"
            ) -or
            (
                [string]$_.body -match $IssueUrlPattern
            ) -or
            (
                [string]$_.title -match "(?i)\b$IssueNumber\b"
            )
        }
    )

    $ExplicitReward = $AllText -match (
        '(?i)' +
        '(?:bounty|reward|payout).{0,100}' +
        '(?:USD|USDC|USDT|\$|€|EUR)\s*[0-9]'
    ) -or $AllText -match (
        '(?i)' +
        '(?:USD|USDC|USDT|\$|€|EUR)\s*[0-9][0-9,.]*' +
        '.{0,100}(?:bounty|reward|payout)'
    )

    $OpenIssue = [string]$Issue.state -eq "OPEN"

    $UniquePrCount    = @($PullRequestReferences).Count
    $AttemptCount     = @($AttemptComments).Count
    $SubmissionCount  = @($SubmissionComments).Count
    $RelatedPrCount   = @($DirectlyRelatedPRs).Count
    $TotalComments    = $Comments.Count

    $CompetitionScore = 0

    $CompetitionScore += [Math]::Min(50, $UniquePrCount * 12)
    $CompetitionScore += [Math]::Min(25, $AttemptCount * 8)
    $CompetitionScore += [Math]::Min(15, $SubmissionCount * 4)
    $CompetitionScore += [Math]::Min(30, $RelatedPrCount * 10)

    $CompetitionLevel = if ($CompetitionScore -ge 50) {
        "SATURATED"
    }
    elseif ($CompetitionScore -ge 25) {
        "HIGH"
    }
    elseif ($CompetitionScore -ge 10) {
        "MODERATE"
    }
    else {
        "LOW"
    }

    @(
        "# Latest Live Candidate Preflight"
        ""
        "- Checked at: ``$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")``"
        "- Repository: ``$Repository``"
        "- Issue: ``$IssueNumber``"
        "- Title: $($Issue.title)"
        "- URL: $($Issue.url)"
        "- State: ``$($Issue.state)``"
        "- Payment confidence: ``$Confidence``"
        "- Explicit executor reward: ``$ExplicitReward``"
        ""
        "## Competition"
        ""
        "- Total comments: ``$TotalComments``"
        "- Attempt/claim comments: ``$AttemptCount``"
        "- Submission comments: ``$SubmissionCount``"
        "- Unique PR references in comments: ``$UniquePrCount``"
        "- Directly related repository PRs: ``$RelatedPrCount``"
        "- Competition score: ``$CompetitionScore``"
        "- Competition level: ``$CompetitionLevel``"
        ""
        "## Pull request references"
        ""
        $(
            if ($UniquePrCount -gt 0) {
                ($PullRequestReferences | ForEach-Object { "- PR #$_" }) -join "`n"
            }
            else {
                "No PR references detected."
            }
        )
    ) | Set-Content $ValidationReport -Encoding UTF8

    Write-Host ""
    Write-Host "Issue aberta       : $OpenIssue"
    Write-Host "Reward explícito   : $ExplicitReward"
    Write-Host "Comentários        : $TotalComments"
    Write-Host "Tentativas         : $AttemptCount"
    Write-Host "Submissões         : $SubmissionCount"
    Write-Host "PRs referenciados  : $UniquePrCount"
    Write-Host "PRs ligados        : $RelatedPrCount"
    Write-Host "Competition score  : $CompetitionScore"
    Write-Host "Competition level  : $CompetitionLevel"

    if (-not $OpenIssue) {
        Add-LiveRejection `
            -Repository $Repository `
            -IssueNumber $IssueNumber `
            -PriorScore $Confidence `
            -Code "ISSUE_NOT_OPEN" `
            -Reason "A oportunidade não está mais aberta." `
            -Evidence "GitHub state: $($Issue.state)."

        continue
    }

    if (-not $ExplicitReward) {
        Add-LiveRejection `
            -Repository $Repository `
            -IssueNumber $IssueNumber `
            -PriorScore $Confidence `
            -Code "EXECUTOR_REWARD_NOT_CONFIRMED_LIVE" `
            -Reason "A leitura ao vivo não confirmou recompensa explicitamente associada ao executor." `
            -Evidence "Título e conteúdo não conectam claramente bounty/reward/payout ao valor monetário."

        continue
    }

    if (
        $CompetitionLevel -eq "SATURATED" -or
        $UniquePrCount -ge 3 -or
        $RelatedPrCount -ge 3 -or
        $AttemptCount -ge 4
    ) {
        $Evidence = (
            "comments=$TotalComments; " +
            "attempts=$AttemptCount; " +
            "submission_comments=$SubmissionCount; " +
            "unique_pr_references=$UniquePrCount; " +
            "related_prs=$RelatedPrCount; " +
            "competition_score=$CompetitionScore"
        )

        Add-LiveRejection `
            -Repository $Repository `
            -IssueNumber $IssueNumber `
            -PriorScore $Confidence `
            -Code "SATURATED_COMPETITION" `
            -Reason "A oportunidade já apresenta concorrência excessiva para o retorno esperado." `
            -Evidence $Evidence

        Write-Host ""
        Write-Host "Candidato rejeitado por concorrência." `
            -ForegroundColor Yellow

        continue
    }

    Write-Host ""
    Write-Host "===== CANDIDATO APROVADO NO LIVE PREFLIGHT =====" `
        -ForegroundColor Green

    $SafeRepoName = $Repository -replace '[^a-zA-Z0-9._-]', '_'
    $TargetWorkspace = Join-Path $WorkspaceRoot $SafeRepoName

    if (-not (Test-Path $TargetWorkspace)) {
        Write-Host "Clonando repositório aprovado..." `
            -ForegroundColor Cyan

        & gh repo clone $Repository $TargetWorkspace

        if ($LASTEXITCODE -ne 0) {
            throw "Falha ao clonar $Repository."
        }
    }
    else {
        Write-Host "Workspace já existe:"
        Write-Host $TargetWorkspace
    }

    $IssueFile = Join-Path `
        $TargetWorkspace `
        "PAYMENT_TARGET_ISSUE.md"

    $PlanFile = Join-Path `
        $TargetWorkspace `
        "EXECUTION_START.md"

    gh issue view $IssueNumber `
        --repo $Repository `
        --comments |
        Set-Content $IssueFile -Encoding UTF8

    @(
        "# Payment Target Execution Start"
        ""
        "- Repository: ``$Repository``"
        "- Issue: ``$IssueNumber``"
        "- Reward USD: ``$($Target.reward_usd)``"
        "- Payment confidence: ``$Confidence``"
        "- Competition level: ``$CompetitionLevel``"
        "- Competition score: ``$CompetitionScore``"
        "- Workspace: ``$TargetWorkspace``"
        "- Started at: ``$(Get-Date -Format "yyyy-MM-dd HH:mm:ss")``"
        ""
        "## Current state"
        ""
        "``LIVE_PAYMENT_AND_COMPETITION_PREFLIGHT_PASSED``"
        ""
        "No issue comment, claim, push, pull request or external commitment"
        "was performed."
    ) | Set-Content $PlanFile -Encoding UTF8

    Write-Host ""
    Write-Host "===== EXECUÇÃO LOCAL AUTORIZADA =====" `
        -ForegroundColor Green
    Write-Host "Repository : $Repository"
    Write-Host "Issue      : $IssueNumber"
    Write-Host "Workspace  : $TargetWorkspace"
    Write-Host "Competition: $CompetitionLevel"
    Write-Host "Report     : $ValidationReport"

    exit 0
}

throw "O limite de seleções foi atingido sem candidato elegível."
