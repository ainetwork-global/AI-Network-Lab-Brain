param(
    [switch]$SkipDiscovery
)

$ErrorActionPreference = "Stop"

$OperationsDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = Split-Path -Parent $OperationsDir

$LogDir = Join-Path $Root "09_LOGS"
$ReportDir = Join-Path $Root "12_REPORTS"
$OpportunityDir = Join-Path $Root "04_OPPORTUNITIES"

New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
New-Item -ItemType Directory -Path $ReportDir -Force | Out-Null

$Timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
$RunLog = Join-Path $LogDir "global_revenue_pipeline_$Timestamp.log"
$StageCsv = Join-Path $LogDir "pipeline_stages_$Timestamp.csv"
$LatestReport = Join-Path $ReportDir "LATEST_GLOBAL_REVENUE_PIPELINE.md"

$Results = New-Object System.Collections.Generic.List[object]

function Write-RunLog {
    param(
        [string]$Message,
        [ConsoleColor]$Color = [ConsoleColor]::Gray
    )

    $Line = "[{0}] {1}" -f `
        (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), `
        $Message

    Write-Host $Line -ForegroundColor $Color
    Add-Content -Path $RunLog -Value $Line -Encoding UTF8
}

function Resolve-Script {
    param(
        [string[]]$CandidateNames
    )

    foreach ($Name in $CandidateNames) {
        $Match = Get-ChildItem `
            -Path $Root `
            -Recurse `
            -File `
            -Filter $Name `
            -ErrorAction SilentlyContinue |
            Select-Object -First 1

        if ($Match) {
            return $Match.FullName
        }
    }

    return $null
}

function Invoke-PythonStage {
    param(
        [string]$Stage,
        [string[]]$CandidateNames,
        [bool]$Required
    )

    $Script = Resolve-Script -CandidateNames $CandidateNames

    if (-not $Script) {
        $Status = if ($Required) {
            "MISSING_REQUIRED"
        }
        else {
            "NOT_FOUND"
        }

        $Results.Add(
            [pscustomobject]@{
                stage = $Stage
                status = $Status
                script = ""
                exit_code = ""
            }
        )

        Write-RunLog "$Stage - script não encontrado." Yellow

        if ($Required) {
            throw "Etapa obrigatória ausente: $Stage"
        }

        return
    }

    Write-RunLog "$Stage - executando: $Script" Cyan

    $Output = & python $Script 2>&1
    $ExitCode = $LASTEXITCODE

    foreach ($OutputLine in $Output) {
        Write-RunLog "  $OutputLine"
    }

    if ($ExitCode -eq 0) {
        $Status = "SUCCESS"
        Write-RunLog "$Stage - concluído." Green
    }
    else {
        $Status = "FAILED"
        Write-RunLog "$Stage - falhou. Código: $ExitCode" Red
    }

    $Results.Add(
        [pscustomobject]@{
            stage = $Stage
            status = $Status
            script = $Script
            exit_code = $ExitCode
        }
    )

    if ($Required -and $ExitCode -ne 0) {
        throw "Falha na etapa obrigatória: $Stage"
    }
}

function Read-CsvSafe {
    param(
        [string]$Path
    )

    if (Test-Path $Path) {
        return @(Import-Csv $Path)
    }

    return @()
}

Write-RunLog "GLOBAL REVENUE PIPELINE INICIADO" Green
Write-RunLog "Root: $Root"
Write-RunLog "SkipDiscovery: $SkipDiscovery"

try {
    if (-not $SkipDiscovery) {
        Write-RunLog "===== DISCOVERY =====" Green

        Invoke-PythonStage `
            -Stage "GitHub Public Discovery" `
            -CandidateNames @(
                "github_public_discovery.py"
            ) `
            -Required $false

        Invoke-PythonStage `
            -Stage "Algora Open Bounty Adapter" `
            -CandidateNames @(
                "algora_open_bounty_adapter.py",
                "algora_adapter.py"
            ) `
            -Required $false

        Invoke-PythonStage `
            -Stage "Devpost Official Adapter" `
            -CandidateNames @(
                "devpost_official_adapter.py",
                "devpost_adapter.py"
            ) `
            -Required $false

        Invoke-PythonStage `
            -Stage "Official Opportunity Discovery" `
            -CandidateNames @(
                "official_opportunity_adapter.py",
                "official_discovery.py",
                "grants_official_adapter.py"
            ) `
            -Required $false
    }
    else {
        Write-RunLog "Discovery ignorado." Yellow
    }

    Write-RunLog "===== INTELLIGENCE =====" Green

    Invoke-PythonStage `
        -Stage "Opportunity Verification Engine" `
        -CandidateNames @(
            "opportunity_verification_engine.py"
        ) `
        -Required $true

    Invoke-PythonStage `
        -Stage "Execution Candidate Ranking" `
        -CandidateNames @(
            "execution_candidate_ranking.py"
        ) `
        -Required $true

    Invoke-PythonStage `
        -Stage "Opportunity Live Validator" `
        -CandidateNames @(
            "opportunity_live_validator.py"
        ) `
        -Required $true

    Write-RunLog "===== EXECUTION =====" Green

    Invoke-PythonStage `
        -Stage "Build Execution Ready Queue" `
        -CandidateNames @(
            "build_execution_ready_queue.py"
        ) `
        -Required $true

    Invoke-PythonStage `
        -Stage "Build Execution Kanban" `
        -CandidateNames @(
            "build_execution_kanban.py"
        ) `
        -Required $true

    Invoke-PythonStage `
        -Stage "Revenue Execution Worker" `
        -CandidateNames @(
            "revenue_execution_worker.py"
        ) `
        -Required $true

    $RankingPath = Join-Path `
        $OpportunityDir `
        "execution_candidate_ranking.csv"

    $LivePath = Join-Path `
        $OpportunityDir `
        "live_validated_opportunities.csv"

    $ReadyPath = Join-Path `
        $OpportunityDir `
        "EXECUTION_READY_QUEUE.csv"

    $KanbanPath = Join-Path `
        $Root `
        "06_OPERATIONS\EXECUTION_KANBAN.csv"

    $NextPath = Join-Path `
        $Root `
        "07_REVENUE_WORKER\NEXT_EXECUTION.md"

    $Ranking = Read-CsvSafe $RankingPath
    $Live = Read-CsvSafe $LivePath
    $Ready = Read-CsvSafe $ReadyPath
    $Kanban = Read-CsvSafe $KanbanPath

    $ReadyTargets = @(
        $Ready |
        Where-Object {
            $_.execution_status -eq "READY_TO_EXECUTE"
        }
    )

    $HumanReviewTargets = @(
        $Ready |
        Where-Object {
            $_.execution_status -eq "HUMAN_REVIEW_REQUIRED"
        }
    )

    $InvalidTargets = @(
        $Ready |
        Where-Object {
            $_.execution_status -eq "INVALID"
        }
    )

    $Top = $Kanban |
        Where-Object {
            $_.status -eq "READY_TO_EXECUTE"
        } |
        Select-Object -First 1

    if (-not $Top) {
        $Top = $Kanban |
            Where-Object {
                $_.status -notin @(
                    "INVALID",
                    "COMPLETED",
                    "PAID",
                    "REJECTED",
                    "CANCELLED",
                    "SUBMITTED"
                )
            } |
            Select-Object -First 1
    }

    $NextContent = ""

    if (Test-Path $NextPath) {
        $NextContent = Get-Content `
            $NextPath `
            -Raw `
            -Encoding UTF8
    }

    if (-not $Top) {
        throw "Nenhum alvo elegível chegou ao Kanban."
    }

    if ($Top.status -eq "INVALID") {
        throw "O primeiro alvo elegível está marcado como INVALID."
    }

    if ($NextContent -match "SecureBananaLabs/bug-bounty") {
        throw "O alvo inválido de USD 700 voltou ao Worker."
    }

    if ($NextContent -notmatch "READY_TO_EXECUTE") {
        throw "O Worker não recebeu um alvo READY_TO_EXECUTE."
    }

    $SuccessCount = @(
        $Results |
        Where-Object {
            $_.status -eq "SUCCESS"
        }
    ).Count

    $FailedCount = @(
        $Results |
        Where-Object {
            $_.status -eq "FAILED"
        }
    ).Count

    $MissingCount = @(
        $Results |
        Where-Object {
            $_.status -in @(
                "NOT_FOUND",
                "MISSING_REQUIRED"
            )
        }
    ).Count

    $Report = New-Object System.Collections.Generic.List[string]

    $Report.Add("# GLOBAL REVENUE PIPELINE")
    $Report.Add("")
    $Report.Add(
        "Generated at: " +
        (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
    )
    $Report.Add("")
    $Report.Add("## Pipeline status")
    $Report.Add("")
    $Report.Add("- Successful stages: $SuccessCount")
    $Report.Add("- Failed optional stages: $FailedCount")
    $Report.Add("- Missing stages: $MissingCount")
    $Report.Add("- Ranked opportunities: $($Ranking.Count)")
    $Report.Add("- Live validated opportunities: $($Live.Count)")
    $Report.Add("- Execution queue opportunities: $($Ready.Count)")
    $Report.Add("- Ready to execute: $($ReadyTargets.Count)")
    $Report.Add("- Human review required: $($HumanReviewTargets.Count)")
    $Report.Add("- Invalid or unavailable: $($InvalidTargets.Count)")
    $Report.Add("")
    $Report.Add("## Stage results")
    $Report.Add("")

    foreach ($Result in $Results) {
        $Report.Add(
            "- " +
            $Result.stage +
            ": " +
            $Result.status
        )
    }

    $Report.Add("")
    $Report.Add("## Current execution target")
    $Report.Add("")
    $Report.Add("- Title: $($Top.title)")
    $Report.Add("- Status: $($Top.status)")
    $Report.Add("- Reward: $($Top.reward)")
    $Report.Add("- Repository: $($Top.repository)")
    $Report.Add("- Issue: $($Top.issue_number)")
    $Report.Add("- URL: $($Top.url)")
    $Report.Add("")
    $Report.Add("## Safety boundary")
    $Report.Add("")
    $Report.Add(
        "Este pipeline identifica, classifica, valida e prepara oportunidades."
    )
    $Report.Add(
        "Ele não reivindica tarefas, não envia código, não cria propostas e não realiza submissões automaticamente."
    )

    Set-Content `
        -Path $LatestReport `
        -Value $Report `
        -Encoding UTF8

    Write-RunLog "===== RESULTADO FINAL =====" Green
    Write-RunLog "Alvo: $($Top.title)" Green
    Write-RunLog "Status: $($Top.status)" Green
    Write-RunLog "Recompensa: $($Top.reward)" Green
    Write-RunLog "Repository: $($Top.repository)" Green
    Write-RunLog "Relatório: $LatestReport" Green
    Write-RunLog "GLOBAL REVENUE PIPELINE CONCLUÍDO" Green
}
catch {
    Write-RunLog "ERRO FATAL: $($_.Exception.Message)" Red
    throw
}
finally {
    $Results |
        Export-Csv `
            -Path $StageCsv `
            -NoTypeInformation `
            -Encoding UTF8
}
