param(
    [Parameter(Mandatory = $true)]
    [string]$SourceRoot,

    [Parameter(Mandatory = $true)]
    [string]$RepoRoot,

    [Parameter(Mandatory = $true)]
    [string]$StatePath,

    [Parameter(Mandatory = $true)]
    [string]$ReportPath
)

$ErrorActionPreference = "Stop"

$Files = @(
    Get-ChildItem -Path $SourceRoot -Recurse -File |
    Where-Object { $_.Extension -in @(".js", ".ts", ".mjs", ".cjs") }
)

$StatePattern = '(?i)\b(status|state|stage|approved|accepted|completed|cancelled|canceled|paid|verified|read|active|role)\b'
$InputPattern = '(?i)\b(req\.body|payload|body|data|input)\b'
$PersistPattern = '(?i)\.(push|splice|update|create|save|set|assign)\s*\(|Object\.assign\s*\('
$PreviousStatePattern = '(?i)\.(status|state|stage)\s*(===|!==|==|!=)|allowedTransitions|transition'
$FinancialPattern = '(?i)\b(payment|stripe|amount|currency|balance|credit|refund|charge|payout|budget|price|fee|total)\b'
$AuthPattern = '(?i)\b(req\.user|request\.user|authenticate|authorize|requireAuth|permission|forbidden)\b'
$GuardPattern = '(?i)\b(if|switch|throw|validate|assert|safeParse)\b'

$Findings = New-Object System.Collections.Generic.List[object]

foreach ($File in $Files) {
    $Text = Get-Content -Path $File.FullName -Raw -ErrorAction SilentlyContinue

    if ([string]::IsNullOrWhiteSpace($Text)) {
        continue
    }

    $Lines = $Text -split "`r?`n"

    for ($Index = 0; $Index -lt $Lines.Count; $Index++) {
        $LineText = $Lines[$Index]

        if ($LineText -notmatch $StatePattern) {
            continue
        }

        $Start = [Math]::Max(0, $Index - 12)
        $End = [Math]::Min($Lines.Count - 1, $Index + 25)
        $Context = ($Lines[$Start..$End] -join "`n")

        $RequestControlled = $Context -match $InputPattern
        $PersistenceDetected = $Context -match $PersistPattern
        $PreviousStateDetected = $Context -match $PreviousStatePattern
        $FinancialDetected = $Context -match $FinancialPattern
        $AuthDetected = $Context -match $AuthPattern
        $GuardDetected = $Context -match $GuardPattern

        $Score = 0

        if ($RequestControlled) { $Score += 25 }
        if ($PersistenceDetected) { $Score += 25 }
        if ($FinancialDetected) { $Score += 20 }
        if (-not $PreviousStateDetected) { $Score += 20 }
        if (-not $AuthDetected) { $Score += 10 }
        if ($GuardDetected) { $Score -= 10 }
        if ($PreviousStateDetected) { $Score -= 30 }

        $Score = [Math]::Max(0, [Math]::Min(100, $Score))

        if ($RequestControlled -and $PersistenceDetected -and -not $PreviousStateDetected -and $FinancialDetected) {
            $Decision = "HIGH_PRIORITY_FINANCIAL_STATE_REVIEW"
            $NextAction = "build_local_financial_transition_test"
        }
        elseif ($RequestControlled -and $PersistenceDetected -and -not $PreviousStateDetected) {
            $Decision = "UNGUARDED_STATE_TRANSITION_REVIEW"
            $NextAction = "build_invalid_sequence_runtime_test"
        }
        elseif (-not $PreviousStateDetected -and $Score -ge 40) {
            $Decision = "STATE_MACHINE_REVIEW_REQUIRED"
            $NextAction = "trace_controller_service_and_previous_states"
        }
        else {
            continue
        }

        $RelativePath = $File.FullName.Replace($RepoRoot + "\", "")

        $Excerpt = ($Context -replace '\s+', ' ').Trim()

        if ($Excerpt.Length -gt 1600) {
            $Excerpt = $Excerpt.Substring(0, 1600)
        }

        $Findings.Add([pscustomobject]@{
            file = $RelativePath
            line = $Index + 1
            source_line = $LineText.Trim()
            request_controlled = $RequestControlled
            persistence_detected = $PersistenceDetected
            previous_state_check_detected = $PreviousStateDetected
            financial_context_detected = $FinancialDetected
            authentication_detected = $AuthDetected
            guard_detected = $GuardDetected
            risk_score = $Score
            decision = $Decision
            recommended_next_action = $NextAction
            excerpt = $Excerpt
        })
    }
}

$Priority = @{
    HIGH_PRIORITY_FINANCIAL_STATE_REVIEW = 3
    UNGUARDED_STATE_TRANSITION_REVIEW = 2
    STATE_MACHINE_REVIEW_REQUIRED = 1
}

$Sorted = @(
    $Findings |
    Sort-Object `
        @{ Expression = { $Priority[$_.decision] }; Descending = $true }, `
        @{ Expression = { $_.risk_score }; Descending = $true }
)

$Financial = @($Sorted | Where-Object { $_.decision -eq "HIGH_PRIORITY_FINANCIAL_STATE_REVIEW" })
$Unguarded = @($Sorted | Where-Object { $_.decision -eq "UNGUARDED_STATE_TRANSITION_REVIEW" })
$StateMachine = @($Sorted | Where-Object { $_.decision -eq "STATE_MACHINE_REVIEW_REQUIRED" })

$Recommended = $null

if ($Financial.Count -gt 0) {
    $OverallDecision = "FINANCIAL_STATE_CANDIDATE_FOUND"
    $Recommended = $Financial[0]
    $RecommendedNextAction = "trace_highest_priority_financial_candidate"
}
elseif ($Unguarded.Count -gt 0) {
    $OverallDecision = "UNGUARDED_STATE_CANDIDATE_FOUND"
    $Recommended = $Unguarded[0]
    $RecommendedNextAction = "trace_highest_priority_state_candidate"
}
elseif ($StateMachine.Count -gt 0) {
    $OverallDecision = "STATE_MACHINE_CANDIDATE_FOUND"
    $Recommended = $StateMachine[0]
    $RecommendedNextAction = "inspect_highest_priority_state_candidate"
}
else {
    $OverallDecision = "NO_BUSINESS_LOGIC_CANDIDATE_FOUND"
    $RecommendedNextAction = "move_to_race_condition_analysis"
}

$GeneratedAt = (Get-Date).ToUniversalTime().ToString("o")

$State = [ordered]@{
    generated_at = $GeneratedAt
    source_files_scanned = $Files.Count
    findings_total = $Sorted.Count
    financial_candidates = $Financial.Count
    unguarded_state_candidates = $Unguarded.Count
    state_machine_candidates = $StateMachine.Count
    overall_decision = $OverallDecision
    recommended_candidate = $Recommended
    recommended_next_action = $RecommendedNextAction
    findings = $Sorted
    original_source_modified = $false
    external_publication_performed = $false
}

$State |
ConvertTo-Json -Depth 20 |
Set-Content -Path $StatePath -Encoding UTF8

$Report = New-Object System.Collections.Generic.List[string]

$Report.Add("# SecureBananaLabs — Business Logic Hunter")
$Report.Add("")
$Report.Add("Gerado em: $GeneratedAt")
$Report.Add("")
$Report.Add("## Resultado")
$Report.Add("")
$Report.Add("- Decisão: **$OverallDecision**")
$Report.Add("- Arquivos analisados: **$($Files.Count)**")
$Report.Add("- Achados: **$($Sorted.Count)**")
$Report.Add("- Candidatos financeiros: **$($Financial.Count)**")
$Report.Add("- Transições sem guarda: **$($Unguarded.Count)**")
$Report.Add("- State-machine candidates: **$($StateMachine.Count)**")
$Report.Add("- Próxima ação: **$RecommendedNextAction**")
$Report.Add("")

if ($null -ne $Recommended) {
    $Report.Add("## Candidato recomendado")
    $Report.Add("")
    $Report.Add("- Arquivo: ``$($Recommended.file)``")
    $Report.Add("- Linha: **$($Recommended.line)**")
    $Report.Add("- Risk score: **$($Recommended.risk_score)**")
    $Report.Add("- Decisão: **$($Recommended.decision)**")
    $Report.Add("- Linha analisada: ``$($Recommended.source_line)``")
    $Report.Add("")
}

$Report.Add("## Top 20")
$Report.Add("")

$Counter = 0

foreach ($Finding in @($Sorted | Select-Object -First 20)) {
    $Counter++
    $Report.Add("### $Counter. $($Finding.file):$($Finding.line)")
    $Report.Add("")
    $Report.Add("- Score: **$($Finding.risk_score)**")
    $Report.Add("- Decisão: **$($Finding.decision)**")
    $Report.Add("- Controlado pela requisição: **$($Finding.request_controlled)**")
    $Report.Add("- Persistência detectada: **$($Finding.persistence_detected)**")
    $Report.Add("- Estado anterior verificado: **$($Finding.previous_state_check_detected)**")
    $Report.Add("- Contexto financeiro: **$($Finding.financial_context_detected)**")
    $Report.Add("")
}

$Report.Add("## Segurança")
$Report.Add("")
$Report.Add("- Código analisado alterado: **não**")
$Report.Add("- Requisição externa executada: **não**")
$Report.Add("- Issue criada: **não**")
$Report.Add("- Pull request criado: **não**")

$Report | Set-Content -Path $ReportPath -Encoding UTF8

Write-Host ""
Write-Host "===== BUSINESS LOGIC HUNTER =====" -ForegroundColor Cyan
Write-Host "Source files scanned:" $Files.Count
Write-Host "Findings total:" $Sorted.Count
Write-Host "Financial candidates:" $Financial.Count
Write-Host "Unguarded state candidates:" $Unguarded.Count
Write-Host "State-machine candidates:" $StateMachine.Count
Write-Host "Overall decision:" $OverallDecision
Write-Host "Recommended next action:" $RecommendedNextAction

if ($null -ne $Recommended) {
    Write-Host ""
    Write-Host "===== RECOMMENDED BUSINESS LOGIC CANDIDATE ====="
    Write-Host "File:" $Recommended.file
    Write-Host "Line:" $Recommended.line
    Write-Host "Source line:" $Recommended.source_line
    Write-Host "Risk score:" $Recommended.risk_score
    Write-Host "Decision:" $Recommended.decision
    Write-Host "Request controlled:" $Recommended.request_controlled
    Write-Host "Persistence detected:" $Recommended.persistence_detected
    Write-Host "Previous-state check:" $Recommended.previous_state_check_detected
    Write-Host "Financial context:" $Recommended.financial_context_detected
}

Write-Host ""
Write-Host "===== TOP BUSINESS LOGIC CANDIDATES ====="

$Counter = 0

foreach ($Finding in @($Sorted | Select-Object -First 10)) {
    $Counter++
    Write-Host ""
    Write-Host "$Counter. $($Finding.file):$($Finding.line)"
    Write-Host "   Source line:" $Finding.source_line
    Write-Host "   Score:" $Finding.risk_score
    Write-Host "   Decision:" $Finding.decision
}

Write-Host ""
Write-Host "===== BUSINESS LOGIC HUNTER SAFETY =====" -ForegroundColor Cyan
Write-Host "Original source modified: no"
Write-Host "External publication performed: no"
Write-Host "Issue created: no"
Write-Host "Comment created: no"
Write-Host "Fork created: no"
Write-Host "Pull request created: no"
Write-Host "State:" $StatePath
Write-Host "Report:" $ReportPath
