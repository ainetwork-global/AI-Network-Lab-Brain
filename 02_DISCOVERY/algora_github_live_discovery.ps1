$ErrorActionPreference = "Stop"

$BrainRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

$OutputCsv = Join-Path `
    $BrainRoot `
    "01_GLOBAL_REVENUE_BRAIN\04_OPPORTUNITIES\algora_github_live_bounties.csv"

$ReportFile = Join-Path `
    $BrainRoot `
    "01_GLOBAL_REVENUE_BRAIN\12_REPORTS\LATEST_ALGORA_GITHUB_LIVE_DISCOVERY.md"

$MinRewardUsd = 25
$MaxPagesPerQuery = 10
$PerPage = 100

$Queries = @(
    'is:issue is:open "algora-pbc" in:comments',
    'is:issue is:open "algora-pbcbot" in:comments',
    'is:issue is:open "Receive payment" "/attempt" "/claim" in:comments',
    'is:issue is:open "100% of the bounty is received" in:comments',
    'is:issue is:open "💎" "bounty" in:comments'
)

function Invoke-GitHubSearchApi {
    param(
        [Parameter(Mandatory)]
        [string]$Query
    )

    $Collected = @()

    for ($Page = 1; $Page -le $MaxPagesPerQuery; $Page++) {
        $EncodedQuery = [uri]::EscapeDataString($Query)

        $Endpoint = (
            "search/issues" +
            "?q=$EncodedQuery" +
            "&sort=updated" +
            "&order=desc" +
            "&per_page=$PerPage" +
            "&page=$Page"
        )

        $Json = gh api `
            --method GET `
            $Endpoint 2>$null

        if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Json)) {
            Write-Host "Busca falhou: $Query / página $Page" `
                -ForegroundColor Yellow
            break
        }

        $Payload = $Json | ConvertFrom-Json
        $Items = @($Payload.items)

        if ($Items.Count -eq 0) {
            break
        }

        $Collected += $Items

        if ($Items.Count -lt $PerPage) {
            break
        }

        Start-Sleep -Milliseconds 250
    }

    return $Collected
}

function Get-RepositoryFromUrl {
    param([string]$RepositoryUrl)

    $Match = [regex]::Match(
        $RepositoryUrl,
        'github\.com/repos/([^/]+/[^/]+)$'
    )

    if ($Match.Success) {
        return $Match.Groups[1].Value
    }

    return ""
}

function Get-RewardAmount {
    param([string]$Text)

    $Patterns = @(
        '(?i)💎\s*\$([0-9][0-9,]*(?:\.[0-9]+)?)\s*bounty',
        '(?i)\$([0-9][0-9,]*(?:\.[0-9]+)?)\s*bounty',
        '(?i)bounty.{0,40}\$([0-9][0-9,]*(?:\.[0-9]+)?)',
        '(?i)/bounty\s+\$?([0-9][0-9,]*(?:\.[0-9]+)?)'
    )

    $Amounts = @()

    foreach ($Pattern in $Patterns) {
        foreach ($Match in [regex]::Matches($Text, $Pattern)) {
            $Number = $Match.Groups[1].Value -replace ',', ''

            try {
                $Amounts += [double]$Number
            }
            catch {
            }
        }
    }

    if ($Amounts.Count -eq 0) {
        return 0
    }

    return ($Amounts | Measure-Object -Maximum).Maximum
}

function Get-Competition {
    param(
        [array]$Comments,
        [string]$Repository,
        [int]$IssueNumber
    )

    $AttemptAuthors = [System.Collections.Generic.HashSet[string]]::new()
    $PrNumbers = [System.Collections.Generic.HashSet[string]]::new()
    $SubmissionCount = 0

    foreach ($Comment in $Comments) {
        $Body = [string]$Comment.body
        $Author = [string]$Comment.author.login

        if (
            $Body -match '(?i)/attempt' -or
            $Body -match '(?i)/claim' -or
            $Body -match '(?i)\bclaiming\b' -or
            $Body -match '(?i)\bworking on\b' -or
            $Body -match '(?i)\bstarted working\b'
        ) {
            if (
                $Author -and
                $Author -notmatch '(?i)algora|bot'
            ) {
                [void]$AttemptAuthors.Add($Author)
            }
        }

        if (
            $Body -match '(?i)\bsubmitted\b' -or
            $Body -match '(?i)\bpull request\b' -or
            $Body -match '(?i)\bmy solution\b'
        ) {
            if ($Author -notmatch '(?i)algora|bot') {
                $SubmissionCount++
            }
        }

        foreach ($Match in [regex]::Matches(
            $Body,
            '(?i)github\.com/[^/\s]+/[^/\s]+/pull/([0-9]+)'
        )) {
            [void]$PrNumbers.Add($Match.Groups[1].Value)
        }

        foreach ($Match in [regex]::Matches(
            $Body,
            '(?i)\bPR\s*#?\s*([0-9]+)\b'
        )) {
            [void]$PrNumbers.Add($Match.Groups[1].Value)
        }
    }

    $PrJson = gh pr list `
        --repo $Repository `
        --state open `
        --limit 200 `
        --json number,title,body,author,url 2>$null

    if (
        $LASTEXITCODE -eq 0 -and
        -not [string]::IsNullOrWhiteSpace($PrJson)
    ) {
        $PullRequests = @($PrJson | ConvertFrom-Json)

        foreach ($Pr in $PullRequests) {
            $PrText = @(
                [string]$Pr.title
                [string]$Pr.body
            ) -join "`n"

            if (
                $PrText -match "(?i)/claim\s*#?$IssueNumber\b" -or
                $PrText -match "(?i)(?:close[sd]?|fix(?:e[sd])?|resolve[sd]?)\s*#?$IssueNumber\b"
            ) {
                [void]$PrNumbers.Add([string]$Pr.number)

                if ($Pr.author.login) {
                    [void]$AttemptAuthors.Add(
                        [string]$Pr.author.login
                    )
                }
            }
        }
    }

    $AttemptCount = $AttemptAuthors.Count
    $PrCount = $PrNumbers.Count

    $Score = 0
    $Score += [Math]::Min(50, $AttemptCount * 10)
    $Score += [Math]::Min(50, $PrCount * 15)
    $Score += [Math]::Min(20, $SubmissionCount * 5)

    $Level = if ($Score -ge 50) {
        "SATURATED"
    }
    elseif ($Score -ge 25) {
        "HIGH"
    }
    elseif ($Score -ge 10) {
        "MODERATE"
    }
    else {
        "LOW"
    }

    return [PSCustomObject]@{
        AttemptCount   = $AttemptCount
        PrCount        = $PrCount
        SubmissionCount = $SubmissionCount
        Score          = $Score
        Level          = $Level
        AttemptAuthors = ($AttemptAuthors | Sort-Object) -join ", "
        PrNumbers      = ($PrNumbers | Sort-Object) -join ", "
    }
}

Write-Host ""
Write-Host "===== ALGORA GITHUB LIVE DISCOVERY =====" `
    -ForegroundColor Cyan

$SearchResults = @()

foreach ($Query in $Queries) {
    Write-Host "Buscando: $Query"
    $SearchResults += @(Invoke-GitHubSearchApi -Query $Query)
}

$UniqueIssues = @{}

foreach ($Item in $SearchResults) {
    $Repository = Get-RepositoryFromUrl `
        -RepositoryUrl ([string]$Item.repository_url)

    if (
        [string]::IsNullOrWhiteSpace($Repository) -or
        -not $Item.number
    ) {
        continue
    }

    $Key = "$($Repository.ToLower())#$($Item.number)"

    if (-not $UniqueIssues.ContainsKey($Key)) {
        $UniqueIssues[$Key] = [PSCustomObject]@{
            Repository  = $Repository
            IssueNumber = [int]$Item.number
            SearchTitle = [string]$Item.title
            SearchUrl   = [string]$Item.html_url
        }
    }
}

Write-Host ""
Write-Host "Issues únicas encontradas: $($UniqueIssues.Count)"

$Rows = @()
$Index = 0

foreach ($Candidate in $UniqueIssues.Values) {
    $Index++

    Write-Host (
        "[$Index/$($UniqueIssues.Count)] " +
        "$($Candidate.Repository)#$($Candidate.IssueNumber)"
    )

    $IssueJson = gh issue view `
        $Candidate.IssueNumber `
        --repo $Candidate.Repository `
        --json number,title,body,state,url,comments,createdAt,updatedAt,labels 2>$null

    if (
        $LASTEXITCODE -ne 0 -or
        [string]::IsNullOrWhiteSpace($IssueJson)
    ) {
        continue
    }

    $Issue = $IssueJson | ConvertFrom-Json

    if ([string]$Issue.state -ne "OPEN") {
        continue
    }

    $Comments = @($Issue.comments)

    $FullText = @(
        [string]$Issue.title
        [string]$Issue.body
        ($Comments | ForEach-Object { [string]$_.body })
    ) -join "`n"

    $HasAlgoraBot = $FullText -match (
        '(?i)algora-pbc|algora-pbcbot|with Algora PBC'
    )

    $HasPaymentInstructions = (
        $FullText -match '(?i)Receive payment'
    ) -and (
        $FullText -match '(?i)100% of the bounty'
    )

    $HasClaimInstructions = (
        $FullText -match '(?i)/attempt'
    ) -and (
        $FullText -match '(?i)/claim'
    )

    if (
        -not $HasAlgoraBot -or
        -not $HasPaymentInstructions -or
        -not $HasClaimInstructions
    ) {
        continue
    }

    $Reward = Get-RewardAmount -Text $FullText

    if ($Reward -lt $MinRewardUsd) {
        continue
    }

    $Competition = Get-Competition `
        -Comments $Comments `
        -Repository $Candidate.Repository `
        -IssueNumber $Candidate.IssueNumber

    $EstimatedHours = 8
    $RevenuePerHour = [Math]::Round(
        $Reward / $EstimatedHours,
        2
    )

    $Rows += [PSCustomObject]@{
        source_name                 = "algora_github_live"
        source_type                 = "canonical_bounty_platform"
        platform                    = "Algora"
        canonical_payment_source    = "true"
        payment_platform_verified   = "true"
        repository                  = $Candidate.Repository
        issue_number                = $Candidate.IssueNumber
        title                       = [string]$Issue.title
        description                 = [string]$Issue.body
        url                         = [string]$Issue.url
        issue_url                   = [string]$Issue.url
        reward                      = $Reward
        reward_usd                  = $Reward
        amount_usd                  = $Reward
        currency                    = "USD"
        status                      = "open"
        bounty_status               = "active"
        payment_terms               = "Algora bounty payable to accepted solver"
        executor_payment_evidence   = "Algora bot states receive payment after reward"
        estimated_hours             = $EstimatedHours
        estimated_revenue_per_hour  = $RevenuePerHour
        comments                    = $Comments.Count
        attempts                    = $Competition.AttemptCount
        pull_requests               = $Competition.PrCount
        competition_score_live      = $Competition.Score
        competition_level_live      = $Competition.Level
        attempt_authors              = $Competition.AttemptAuthors
        related_pr_numbers          = $Competition.PrNumbers
        created_at                  = [string]$Issue.createdAt
        updated_at                  = [string]$Issue.updatedAt
        discovered_at               = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    }

    Start-Sleep -Milliseconds 150
}

$Rows = @(
    $Rows |
        Sort-Object `
            @{ Expression = {
                $_.competition_level_live -eq "LOW"
            }; Descending = $true },
            @{ Expression = {
                [double]$_.reward_usd
            }; Descending = $true }
)

$Rows |
    Export-Csv `
        $OutputCsv `
        -NoTypeInformation `
        -Encoding UTF8

$LowRows = @(
    $Rows | Where-Object {
        $_.competition_level_live -eq "LOW"
    }
)

$ReportLines = @(
    "# Latest Algora GitHub Live Discovery",
    "",
    "- Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')",
    "- Raw search records: $($SearchResults.Count)",
    "- Unique issues inspected: $($UniqueIssues.Count)",
    "- Canonical active bounties >= USD $MinRewardUsd`: $($Rows.Count)",
    "- Low competition: $($LowRows.Count)",
    "",
    "## Candidates",
    "",
    "| Reward | Repository | Issue | Competition | Attempts | PRs | Title |",
    "|---:|---|---:|---|---:|---:|---|"
)

foreach ($Row in ($Rows | Select-Object -First 50)) {
    $SafeTitle = ([string]$Row.title) -replace '\|', '/'

    $ReportLines += (
        "| `$$($Row.reward_usd) | " +
        "$($Row.repository) | " +
        "$($Row.issue_number) | " +
        "$($Row.competition_level_live) | " +
        "$($Row.attempts) | " +
        "$($Row.pull_requests) | " +
        "$SafeTitle |"
    )
}

$ReportLines |
    Set-Content $ReportFile -Encoding UTF8

Write-Host ""
Write-Host "===== ALGORA GITHUB LIVE RESULT =====" `
    -ForegroundColor Green

Write-Host "Raw search records : $($SearchResults.Count)"
Write-Host "Unique issues      : $($UniqueIssues.Count)"
Write-Host "Canonical bounties : $($Rows.Count)"
Write-Host "Low competition    : $($LowRows.Count)"

$Rows |
    Select-Object -First 20 `
        reward_usd,
        repository,
        issue_number,
        competition_level_live,
        attempts,
        pull_requests,
        title |
    Format-Table -Wrap -AutoSize

