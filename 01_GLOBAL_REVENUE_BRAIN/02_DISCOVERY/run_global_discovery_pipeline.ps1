param(
    [switch]$SkipGitHubSearch
)

$ErrorActionPreference = "Stop"

$BrainRoot = Split-Path -Parent $PSScriptRoot
$DiscoveryRoot = Join-Path $BrainRoot "02_DISCOVERY"
$OpportunityRoot = Join-Path $BrainRoot "04_OPPORTUNITIES"
$ReportRoot = Join-Path $BrainRoot "12_REPORTS"
$LogRoot = Join-Path $BrainRoot "09_LOGS"

$GitHubScript = Join-Path $DiscoveryRoot "01_GITHUB\github_search_api_discovery.py"
$MergeScript = Join-Path $DiscoveryRoot "09_SHARED\merge_discovery_sources.py"
$IntelligenceScript = Join-Path $BrainRoot "03_INTELLIGENCE\discovery_intelligence.py"

$DiscoveryQueue = Join-Path $OpportunityRoot "GLOBAL_DISCOVERY_QUEUE.csv"
$IntelligenceQueue = Join-Path $OpportunityRoot "DISCOVERY_INTELLIGENCE_QUEUE.csv"

$ReportFile = Join-Path $ReportRoot "LATEST_GLOBAL_DISCOVERY_PIPELINE.md"
$LogFile = Join-Path $LogRoot (
    "global_discovery_pipeline_" +
    (Get-Date -Format "yyyyMMdd_HHmmss") +
    ".log"
)

New-Item -ItemType Directory -Force -Path $OpportunityRoot | Out-Null
New-Item -ItemType Directory -Force -Path $ReportRoot | Out-Null
New-Item -ItemType Directory -Force -Path $LogRoot | Out-Null

$StartedAt = Get-Date
$Steps = [System.Collections.Generic.List[object]]::new()

function Invoke-PipelineStep {
    param(
        [string]$Name,
        [string]$ScriptPath,
        [switch]$Optional
    )

    $StepStarted = Get-Date

    if (-not (Test-Path $ScriptPath)) {
        if ($Optional) {
            $Steps.Add([pscustomobject]@{
                Step = $Name
                Status = "SKIPPED"
                DurationSeconds = 0
                Detail = "Arquivo não encontrado: $ScriptPath"
            })

            return
        }

        throw "Arquivo obrigatório não encontrado: $ScriptPath"
    }

    Write-Host ""
    Write-Host ("=" * 72) -ForegroundColor DarkGray
    Write-Host $Name -ForegroundColor Cyan
    Write-Host ("=" * 72) -ForegroundColor DarkGray

    try {
        $Output = & python $ScriptPath 2>&1

        $Output | Tee-Object -FilePath $LogFile -Append | ForEach-Object {
            Write-Host $_
        }

        if ($LASTEXITCODE -ne 0) {
            throw "Python retornou código $LASTEXITCODE"
        }

        $Duration = [math]::Round(
            ((Get-Date) - $StepStarted).TotalSeconds,
            2
        )

        $Steps.Add([pscustomobject]@{
            Step = $Name
            Status = "SUCCESS"
            DurationSeconds = $Duration
            Detail = ""
        })
    }
    catch {
        $Duration = [math]::Round(
            ((Get-Date) - $StepStarted).TotalSeconds,
            2
        )

        $Steps.Add([pscustomobject]@{
            Step = $Name
            Status = "FAILED"
            DurationSeconds = $Duration
            Detail = $_.Exception.Message
        })

        throw
    }
}

try {
    if (-not $SkipGitHubSearch) {
        Invoke-PipelineStep `
            -Name "GitHub Search API Discovery" `
            -ScriptPath $GitHubScript
    }
    else {
        $Steps.Add([pscustomobject]@{
            Step = "GitHub Search API Discovery"
            Status = "SKIPPED"
            DurationSeconds = 0
            Detail = "Execução iniciada com -SkipGitHubSearch"
        })
    }

    Invoke-PipelineStep `
        -Name "Merge Discovery Sources" `
        -ScriptPath $MergeScript

    Invoke-PipelineStep `
        -Name "Discovery Intelligence" `
        -ScriptPath $IntelligenceScript
}
catch {
    Write-Host ""
    Write-Host "PIPELINE INTERROMPIDO: $($_.Exception.Message)" `
        -ForegroundColor Red
}

$FinishedAt = Get-Date
$DurationTotal = [math]::Round(
    ($FinishedAt - $StartedAt).TotalSeconds,
    2
)

$DiscoveryRows = @()
$IntelligenceRows = @()

if (Test-Path $DiscoveryQueue) {
    $DiscoveryRows = @(Import-Csv $DiscoveryQueue)
}

if (Test-Path $IntelligenceQueue) {
    $IntelligenceRows = @(Import-Csv $IntelligenceQueue)
}

$VeryHigh = @(
    $IntelligenceRows |
    Where-Object { $_.discovery_priority -eq "VERY_HIGH" }
).Count

$High = @(
    $IntelligenceRows |
    Where-Object { $_.discovery_priority -eq "HIGH" }
).Count

$Medium = @(
    $IntelligenceRows |
    Where-Object { $_.discovery_priority -eq "MEDIUM" }
).Count

$Low = @(
    $IntelligenceRows |
    Where-Object { $_.discovery_priority -eq "LOW" }
).Count

$TopCandidates = @(
    $IntelligenceRows |
    Sort-Object {
        [double]($_.discovery_score)
    } -Descending |
    Select-Object -First 20
)

$Lines = [System.Collections.Generic.List[string]]::new()

$Lines.Add("# GLOBAL DISCOVERY PIPELINE")
$Lines.Add("")
$Lines.Add("Generated: $($FinishedAt.ToString('yyyy-MM-dd HH:mm:ss'))")
$Lines.Add("")
$Lines.Add("## Summary")
$Lines.Add("")
$Lines.Add("- Duration seconds: $DurationTotal")
$Lines.Add("- Unique discovered opportunities: $($DiscoveryRows.Count)")
$Lines.Add("- Intelligence-ranked opportunities: $($IntelligenceRows.Count)")
$Lines.Add("- Very high priority: $VeryHigh")
$Lines.Add("- High priority: $High")
$Lines.Add("- Medium priority: $Medium")
$Lines.Add("- Low priority: $Low")
$Lines.Add("")
$Lines.Add("## Pipeline Steps")
$Lines.Add("")
$Lines.Add("| Step | Status | Seconds | Detail |")
$Lines.Add("|---|---:|---:|---|")

foreach ($Step in $Steps) {
    $SafeDetail = ($Step.Detail -replace "\|", "/")
    $Lines.Add(
        "| $($Step.Step) | $($Step.Status) | " +
        "$($Step.DurationSeconds) | $SafeDetail |"
    )
}

$Lines.Add("")
$Lines.Add("## Top Discovery Candidates")
$Lines.Add("")
$Lines.Add(
    "| Rank | Repository | Issue | Score | Priority | Title |"
)
$Lines.Add(
    "|---:|---|---:|---:|---|---|"
)

$Rank = 0

foreach ($Candidate in $TopCandidates) {
    $Rank++

    $Title = (
        [string]$Candidate.title
    ) -replace "\|", "/" -replace "`r|`n", " "

    $Repository = (
        [string]$Candidate.repository
    ) -replace "\|", "/"

    $Lines.Add(
        "| $Rank | $Repository | " +
        "$($Candidate.issue_number) | " +
        "$($Candidate.discovery_score) | " +
        "$($Candidate.discovery_priority) | $Title |"
    )
}

$Lines.Add("")
$Lines.Add("## Files")
$Lines.Add("")
$Lines.Add("- GLOBAL_DISCOVERY_QUEUE.csv")
$Lines.Add("- DISCOVERY_INTELLIGENCE_QUEUE.csv")
$Lines.Add("- Log: $([System.IO.Path]::GetFileName($LogFile))")

$Lines | Set-Content $ReportFile -Encoding UTF8

Write-Host ""
Write-Host ("=" * 72) -ForegroundColor Green
Write-Host "GLOBAL DISCOVERY PIPELINE FINALIZADO" -ForegroundColor Green
Write-Host ("=" * 72) -ForegroundColor Green
Write-Host "Descobertas únicas: $($DiscoveryRows.Count)"
Write-Host "Oportunidades ranqueadas: $($IntelligenceRows.Count)"
Write-Host "VERY_HIGH: $VeryHigh"
Write-Host "HIGH: $High"
Write-Host "Relatório: $ReportFile"
Write-Host "Log: $LogFile"

if ($TopCandidates.Count -gt 0) {
    Write-Host ""
    Write-Host "TOP 10 DESCOBERTAS" -ForegroundColor Yellow

    $TopCandidates |
        Select-Object -First 10 `
            repository,
            issue_number,
            discovery_score,
            discovery_priority,
            title |
        Format-Table -AutoSize
}

if (@($Steps | Where-Object Status -eq "FAILED").Count -gt 0) {
    exit 1
}

exit 0
