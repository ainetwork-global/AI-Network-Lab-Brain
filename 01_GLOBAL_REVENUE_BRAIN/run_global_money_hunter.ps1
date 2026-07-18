param(
    [switch]$SkipGitHubSearch,

    [int]$MaxCandidates = 50,

    [double]$MinPromotionScore = 60
)

$ErrorActionPreference = "Stop"

$BrainRoot = $PSScriptRoot

$DiscoveryPipeline = Join-Path `
    $BrainRoot `
    "02_DISCOVERY\run_global_discovery_pipeline.ps1"

$PromotionGate = Join-Path `
    $BrainRoot `
    "03_INTELLIGENCE\discovery_promotion_gate.py"

$PromotionAdapter = Join-Path `
    $BrainRoot `
    "03_INTELLIGENCE\promoted_discovery_execution_adapter.py"

$RevenuePipeline = Join-Path `
    $BrainRoot `
    "run_global_revenue_pipeline.ps1"

if (-not (Test-Path $RevenuePipeline)) {
    $RevenuePipeline = Get-ChildItem `
        $BrainRoot `
        -Recurse `
        -File `
        -Filter "run_global_revenue_pipeline.ps1" |
        Select-Object -First 1 |
        ForEach-Object FullName
}

$ReportDirectory = Join-Path $BrainRoot "12_REPORTS"
$LogDirectory = Join-Path $BrainRoot "09_LOGS"

$ReportFile = Join-Path `
    $ReportDirectory `
    "LATEST_GLOBAL_MONEY_HUNTER.md"

$LogFile = Join-Path `
    $LogDirectory `
    (
        "global_money_hunter_" +
        (Get-Date -Format "yyyyMMdd_HHmmss") +
        ".log"
    )

New-Item `
    -ItemType Directory `
    -Force `
    -Path $ReportDirectory |
    Out-Null

New-Item `
    -ItemType Directory `
    -Force `
    -Path $LogDirectory |
    Out-Null

$StartedAt = Get-Date

$Steps = [System.Collections.Generic.List[object]]::new()

function Add-StepResult {
    param(
        [string]$Name,
        [string]$Status,
        [double]$Duration,
        [string]$Detail
    )

    $Steps.Add(
        [pscustomobject]@{
            Name = $Name
            Status = $Status
            Duration = $Duration
            Detail = $Detail
        }
    )
}

function Invoke-PythonStage {
    param(
        [string]$Name,
        [string]$Script,
        [string[]]$Arguments = @()
    )

    if (-not (Test-Path $Script)) {
        throw "Arquivo obrigatório não encontrado: $Script"
    }

    Write-Host ""
    Write-Host ("=" * 72) -ForegroundColor DarkGray
    Write-Host $Name -ForegroundColor Cyan
    Write-Host ("=" * 72) -ForegroundColor DarkGray

    $StageStarted = Get-Date

    try {
        $Output = & python $Script @Arguments 2>&1

        $Output |
            Tee-Object `
                -FilePath $LogFile `
                -Append |
            ForEach-Object {
                Write-Host $_
            }

        if ($LASTEXITCODE -ne 0) {
            throw "Python retornou código $LASTEXITCODE"
        }

        $Duration = [math]::Round(
            ((Get-Date) - $StageStarted).TotalSeconds,
            2
        )

        Add-StepResult `
            -Name $Name `
            -Status "SUCCESS" `
            -Duration $Duration `
            -Detail ""
    }
    catch {
        $Duration = [math]::Round(
            ((Get-Date) - $StageStarted).TotalSeconds,
            2
        )

        Add-StepResult `
            -Name $Name `
            -Status "FAILED" `
            -Duration $Duration `
            -Detail $_.Exception.Message

        throw
    }
}

function Invoke-PowerShellStage {
    param(
        [string]$Name,
        [string]$Script,
        [string[]]$Arguments = @()
    )

    if (-not (Test-Path $Script)) {
        throw "Arquivo obrigatório não encontrado: $Script"
    }

    Write-Host ""
    Write-Host ("=" * 72) -ForegroundColor DarkGray
    Write-Host $Name -ForegroundColor Cyan
    Write-Host ("=" * 72) -ForegroundColor DarkGray

    $StageStarted = Get-Date

    try {
        $Output = & powershell.exe `
            -NoProfile `
            -ExecutionPolicy Bypass `
            -File $Script `
            @Arguments 2>&1

        $Output |
            Tee-Object `
                -FilePath $LogFile `
                -Append |
            ForEach-Object {
                Write-Host $_
            }

        if ($LASTEXITCODE -ne 0) {
            throw "PowerShell retornou código $LASTEXITCODE"
        }

        $Duration = [math]::Round(
            ((Get-Date) - $StageStarted).TotalSeconds,
            2
        )

        Add-StepResult `
            -Name $Name `
            -Status "SUCCESS" `
            -Duration $Duration `
            -Detail ""
    }
    catch {
        $Duration = [math]::Round(
            ((Get-Date) - $StageStarted).TotalSeconds,
            2
        )

        Add-StepResult `
            -Name $Name `
            -Status "FAILED" `
            -Duration $Duration `
            -Detail $_.Exception.Message

        throw
    }
}

$PipelineFailed = $false
$FailureMessage = ""

try {
    $DiscoveryArguments = @()

    if ($SkipGitHubSearch) {
        $DiscoveryArguments += "-SkipGitHubSearch"
    }

    Invoke-PowerShellStage `
        -Name "Global Discovery Pipeline" `
        -Script $DiscoveryPipeline `
        -Arguments $DiscoveryArguments

    Invoke-PythonStage `
        -Name "Discovery Promotion Gate" `
        -Script $PromotionGate

    Invoke-PythonStage `
        -Name "Promoted Discovery Integration" `
        -Script $PromotionAdapter `
        -Arguments @(
            "--max-candidates",
            [string]$MaxCandidates,
            "--min-promotion-score",
            [string]$MinPromotionScore
        )

    Invoke-PowerShellStage `
        -Name "Global Revenue Pipeline" `
        -Script $RevenuePipeline `
        -Arguments @("-SkipDiscovery")
}
catch {
    $PipelineFailed = $true
    $FailureMessage = $_.Exception.Message

    Write-Host ""
    Write-Host "GLOBAL MONEY HUNTER INTERROMPIDO" `
        -ForegroundColor Red

    Write-Host $FailureMessage -ForegroundColor Red
}

$FinishedAt = Get-Date

$DurationTotal = [math]::Round(
    ($FinishedAt - $StartedAt).TotalSeconds,
    2
)

$OpportunityDirectory = Join-Path `
    $BrainRoot `
    "04_OPPORTUNITIES"

function Count-CsvRows {
    param([string]$Path)

    if (-not (Test-Path $Path)) {
        return 0
    }

    return @(Import-Csv $Path).Count
}

$DiscoveryCount = Count-CsvRows (
    Join-Path `
        $OpportunityDirectory `
        "GLOBAL_DISCOVERY_QUEUE.csv"
)

$RankedDiscoveryCount = Count-CsvRows (
    Join-Path `
        $OpportunityDirectory `
        "DISCOVERY_INTELLIGENCE_QUEUE.csv"
)

$PromotedCount = Count-CsvRows (
    Join-Path `
        $OpportunityDirectory `
        "DISCOVERY_PROMOTED_QUEUE.csv"
)

$BlockedCount = Count-CsvRows (
    Join-Path `
        $OpportunityDirectory `
        "DISCOVERY_BLOCKED_QUEUE.csv"
)

$ExecutionQueueCount = Count-CsvRows (
    Join-Path `
        $OpportunityDirectory `
        "GLOBAL_EXECUTION_QUEUE.csv"
)

$NextExecution = Get-ChildItem `
    $BrainRoot `
    -Recurse `
    -File `
    -Filter "NEXT_EXECUTION.md" |
    Select-Object -First 1

$Lines = [System.Collections.Generic.List[string]]::new()

$Lines.Add("# GLOBAL MONEY HUNTER")
$Lines.Add("")
$Lines.Add(
    "Generated: " +
    $FinishedAt.ToString("yyyy-MM-dd HH:mm:ss")
)
$Lines.Add("")
$Lines.Add("## Status")
$Lines.Add("")

if ($PipelineFailed) {
    $Lines.Add("- Pipeline status: FAILED")
    $Lines.Add(
        "- Failure: " +
        ($FailureMessage -replace "\|", "/")
    )
}
else {
    $Lines.Add("- Pipeline status: SUCCESS")
}

$Lines.Add("- Duration seconds: $DurationTotal")
$Lines.Add("- Discovered opportunities: $DiscoveryCount")
$Lines.Add(
    "- Intelligence-ranked opportunities: " +
    $RankedDiscoveryCount
)
$Lines.Add("- Promoted opportunities: $PromotedCount")
$Lines.Add("- Blocked opportunities: $BlockedCount")
$Lines.Add(
    "- Global execution queue: " +
    $ExecutionQueueCount
)
$Lines.Add(
    "- Maximum promoted candidates per run: " +
    $MaxCandidates
)
$Lines.Add(
    "- Minimum promotion score: " +
    $MinPromotionScore
)

$Lines.Add("")
$Lines.Add("## Pipeline Stages")
$Lines.Add("")
$Lines.Add("| Stage | Status | Seconds | Detail |")
$Lines.Add("|---|---|---:|---|")

foreach ($Step in $Steps) {
    $Detail = (
        [string]$Step.Detail
    ) -replace "\|", "/" -replace "`r|`n", " "

    $Lines.Add(
        "| $($Step.Name) | " +
        "$($Step.Status) | " +
        "$($Step.Duration) | " +
        "$Detail |"
    )
}

if ($NextExecution) {
    $Lines.Add("")
    $Lines.Add("## Current Next Execution")
    $Lines.Add("")

    foreach (
        $Line in Get-Content $NextExecution.FullName
    ) {
        $Lines.Add($Line)
    }
}

$Lines.Add("")
$Lines.Add("## Log")
$Lines.Add("")
$Lines.Add(
    "- " +
    [System.IO.Path]::GetFileName($LogFile)
)

$Lines |
    Set-Content `
        $ReportFile `
        -Encoding UTF8

Write-Host ""
Write-Host ("=" * 72) -ForegroundColor Green
Write-Host "GLOBAL MONEY HUNTER FINALIZADO" `
    -ForegroundColor Green
Write-Host ("=" * 72) -ForegroundColor Green

Write-Host "Descobertas: $DiscoveryCount"
Write-Host "Promovidas: $PromotedCount"
Write-Host "Bloqueadas: $BlockedCount"
Write-Host "Fila econômica: $ExecutionQueueCount"
Write-Host "Relatório: $ReportFile"
Write-Host "Log: $LogFile"

if ($NextExecution) {
    Write-Host ""
    Write-Host "===== PRÓXIMA EXECUÇÃO =====" `
        -ForegroundColor Yellow

    Get-Content $NextExecution.FullName
}

if ($PipelineFailed) {
    exit 1
}

exit 0
