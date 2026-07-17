param(
    [Parameter(Mandatory = $true)][string]$SourceRoot,
    [Parameter(Mandatory = $true)][string]$TargetRepo,
    [Parameter(Mandatory = $true)][string]$StatePath,
    [Parameter(Mandatory = $true)][string]$ReportPath
)

$ErrorActionPreference = "Stop"

function Read-Source {
    param([string]$Path)

    if (Test-Path $Path) {
        return Get-Content -Path $Path -Raw -ErrorAction Stop
    }

    return ""
}

function Relative-Path {
    param([string]$Path)

    return $Path.Replace($TargetRepo + "\", "")
}

$CandidateFiles = @(
    Get-ChildItem -Path $SourceRoot -Recurse -File |
    Where-Object {
        $_.Extension -in @(".js", ".ts", ".mjs", ".cjs") -and
        (
            $_.Name -match "job" -or
            (Get-Content $_.FullName -Raw -ErrorAction SilentlyContinue) -match "createJob"
        )
    }
)

$FileEvidence = New-Object System.Collections.Generic.List[object]

foreach ($File in $CandidateFiles) {
    $Text = Read-Source $File.FullName

    if ([string]::IsNullOrWhiteSpace($Text)) {
        continue
    }

    $Evidence = [ordered]@{
        file = Relative-Path $File.FullName
        contains_create_job = [bool]($Text -match '(?i)\bcreateJob\b')
        contains_status_open = [bool]($Text -match '(?i)status\s*:\s*["'']open["'']')
        spreads_payload_after_status = [bool](
            $Text -match '(?is)status\s*:\s*["'']open["'']\s*,\s*\.\.\.\s*payload'
        )
        spreads_body_after_status = [bool](
            $Text -match '(?is)status\s*:\s*["'']open["'']\s*,\s*\.\.\.\s*(?:req\.body|body|data|input)'
        )
        validator_mentions_status = [bool](
            $Text -match '(?i)\bstatus\b'
        )
        validator_rejects_status = [bool](
            $Text -match '(?is)(strict\s*\(\)|unrecognized_keys|additionalProperties\s*:\s*false)'
        )
        route_post_detected = [bool](
            $Text -match '(?i)\.(post|put|patch)\s*\('
        )
        authentication_detected = [bool](
            $Text -match '(?i)authenticate|authorize|requireAuth|verifyToken|req\.user'
        )
        excerpt = ""
    }

    $Match = [regex]::Match(
        $Text,
        '(?is).{0,500}(?:createJob|status\s*:\s*["'']open["'']).{0,1200}'
    )

    if ($Match.Success) {
        $Excerpt = ($Match.Value -replace '\s+', ' ').Trim()

        if ($Excerpt.Length -gt 1700) {
            $Excerpt = $Excerpt.Substring(0, 1700)
        }

        $Evidence.excerpt = $Excerpt
    }

    $FileEvidence.Add([pscustomobject]$Evidence)
}

$ServiceEvidence = @(
    $FileEvidence |
    Where-Object {
        $_.spreads_payload_after_status -or
        $_.spreads_body_after_status
    }
)

$ValidatorFiles = @(
    $FileEvidence |
    Where-Object {
        $_.file -match '(?i)validator|schema'
    }
)

$StatusValidated = [bool](
    $ValidatorFiles |
    Where-Object {
        $_.validator_mentions_status
    }
)

$UnknownFieldsRejected = [bool](
    $ValidatorFiles |
    Where-Object {
        $_.validator_rejects_status
    }
)

$Queries = @(
    '"job creation" "status" override'
    '"job service" "client-controlled status"'
    '"job status" "payload"'
    '"status open" "job"'
    '"job creation" "preserve server" status'
)

$OnlineIssues = New-Object System.Collections.Generic.List[object]
$SeenNumbers = @{}

foreach ($Query in $Queries) {
    $Raw = gh search issues $Query `
        --repo SecureBananaLabs/securebananalabs-bug-bounty-743 `
        --state open `
        --limit 30 `
        --json number,title,url,state 2>$null

    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Raw)) {
        continue
    }

    $Items = @($Raw | ConvertFrom-Json)

    foreach ($Item in $Items) {
        if ($SeenNumbers.ContainsKey([string]$Item.number)) {
            continue
        }

        $SeenNumbers[[string]$Item.number] = $true

        $Title = [string]$Item.title
        $Score = 0

        if ($Title -match '(?i)\bjob\b') { $Score += 30 }
        if ($Title -match '(?i)\bstatus\b') { $Score += 30 }
        if ($Title -match '(?i)override|client-controlled|caller-controlled') { $Score += 30 }
        if ($Title -match '(?i)creation|create') { $Score += 10 }

        if ($Score -ge 40) {
            $OnlineIssues.Add([pscustomobject]@{
                number = $Item.number
                title = $Title
                url = $Item.url
                relevance_score = $Score
            })
        }
    }
}

$RankedIssues = @(
    $OnlineIssues |
    Sort-Object relevance_score -Descending
)

$StrongMatches = @(
    $RankedIssues |
    Where-Object {
        $_.relevance_score -ge 70
    }
)

$OverrideDetected = $ServiceEvidence.Count -gt 0
$DuplicateBlocked = $StrongMatches.Count -gt 0

if (-not $OverrideDetected) {
    $OverallDecision = "JOB_STATUS_OVERRIDE_NOT_DETECTED"
    $NextAction = "move_to_next_business_logic_candidate"
}
elseif ($StatusValidated -and $UnknownFieldsRejected) {
    $OverallDecision = "STATUS_INPUT_BLOCKED_BY_VALIDATOR"
    $NextAction = "discard_candidate"
}
elseif ($DuplicateBlocked) {
    $OverallDecision = "JOB_STATUS_CANDIDATE_DUPLICATE_OR_OCCUPIED"
    $NextAction = "move_to_next_business_logic_candidate"
}
elseif ($StatusValidated) {
    $OverallDecision = "JOB_STATUS_VALIDATION_REQUIRES_RUNTIME_PROOF"
    $NextAction = "build_isolated_job_status_runtime_test"
}
else {
    $OverallDecision = "JOB_STATUS_OVERRIDE_RUNTIME_PROOF_REQUIRED"
    $NextAction = "build_isolated_job_status_runtime_test"
}

$GeneratedAt = (Get-Date).ToUniversalTime().ToString("o")

$State = [ordered]@{
    generated_at = $GeneratedAt
    candidate = "job_creation_status_override"
    files_inspected = $CandidateFiles.Count
    override_pattern_detected = $OverrideDetected
    service_evidence = $ServiceEvidence
    status_mentioned_by_validator = $StatusValidated
    unknown_fields_rejected = $UnknownFieldsRejected
    strong_online_matches = $StrongMatches
    all_online_matches = $RankedIssues
    duplicate_blocked = $DuplicateBlocked
    overall_decision = $OverallDecision
    recommended_next_action = $NextAction
    github_search_mode = "read_only"
    original_source_modified = $false
    dependency_install_performed = $false
    runtime_execution_performed = $false
    issue_created = $false
    comment_created = $false
    fork_created = $false
    pull_request_created = $false
}

$State |
ConvertTo-Json -Depth 20 |
Set-Content -Path $StatePath -Encoding UTF8

$Report = New-Object System.Collections.Generic.List[string]

$Report.Add("# SecureBananaLabs — Job Status Gate")
$Report.Add("")
$Report.Add("Gerado em: $GeneratedAt")
$Report.Add("")
$Report.Add("## Resultado")
$Report.Add("")
$Report.Add("- Decisão: **$OverallDecision**")
$Report.Add("- Padrão de sobrescrita detectado: **$OverrideDetected**")
$Report.Add("- Status mencionado no validator: **$StatusValidated**")
$Report.Add("- Campos desconhecidos rejeitados: **$UnknownFieldsRejected**")
$Report.Add("- Correspondências online fortes: **$($StrongMatches.Count)**")
$Report.Add("- Bloqueado por duplicata: **$DuplicateBlocked**")
$Report.Add("- Próxima ação: **$NextAction**")
$Report.Add("")

$Report.Add("## Evidência local")
$Report.Add("")

foreach ($Item in $ServiceEvidence) {
    $Report.Add("### $($Item.file)")
    $Report.Add("")
    $Report.Add("- Payload após status: **$($Item.spreads_payload_after_status)**")
    $Report.Add("- Body após status: **$($Item.spreads_body_after_status)**")
    $Report.Add("")
    $Report.Add("```javascript")
    $Report.Add($Item.excerpt)
    $Report.Add("```")
    $Report.Add("")
}

$Report.Add("## Issues semelhantes")
$Report.Add("")

if ($RankedIssues.Count -eq 0) {
    $Report.Add("Nenhuma correspondência relevante foi encontrada pela pesquisa atual.")
    $Report.Add("")
}
else {
    foreach ($Issue in @($RankedIssues | Select-Object -First 20)) {
        $Report.Add(
            "- #$($Issue.number) — $($Issue.title) — relevância $($Issue.relevance_score)"
        )
    }

    $Report.Add("")
}

$Report.Add("## Segurança")
$Report.Add("")
$Report.Add("- Pesquisa GitHub: **somente leitura**")
$Report.Add("- Código original alterado: **não**")
$Report.Add("- Dependências instaladas: **não**")
$Report.Add("- Teste de runtime executado: **não**")
$Report.Add("- Issue criada: **não**")
$Report.Add("- Comentário criado: **não**")
$Report.Add("- Fork criado: **não**")
$Report.Add("- Pull request criado: **não**")

$Report |
Set-Content -Path $ReportPath -Encoding UTF8

Write-Host ""
Write-Host "===== JOB STATUS GATE =====" -ForegroundColor Cyan
Write-Host "Files inspected:" $CandidateFiles.Count
Write-Host "Override pattern detected:" $OverrideDetected
Write-Host "Status mentioned by validator:" $StatusValidated
Write-Host "Unknown fields rejected:" $UnknownFieldsRejected
Write-Host "Strong online matches:" $StrongMatches.Count
Write-Host "Duplicate blocked:" $DuplicateBlocked
Write-Host "Overall decision:" $OverallDecision
Write-Host "Recommended next action:" $NextAction

Write-Host ""
Write-Host "===== LOCAL JOB STATUS EVIDENCE ====="

foreach ($Item in $ServiceEvidence) {
    Write-Host ""
    Write-Host "File:" $Item.file
    Write-Host "Payload after status:" $Item.spreads_payload_after_status
    Write-Host "Body after status:" $Item.spreads_body_after_status
    Write-Host "Excerpt:" $Item.excerpt
}

Write-Host ""
Write-Host "===== STRONG ONLINE MATCHES ====="

if ($StrongMatches.Count -eq 0) {
    Write-Host "None"
}
else {
    foreach ($Issue in $StrongMatches) {
        Write-Host "#$($Issue.number) $($Issue.title) (relevance $($Issue.relevance_score))"
    }
}

Write-Host ""
Write-Host "===== JOB STATUS GATE SAFETY =====" -ForegroundColor Cyan
Write-Host "GitHub search mode: read only"
Write-Host "Original source modified: no"
Write-Host "Dependency install performed: no"
Write-Host "Runtime execution performed: no"
Write-Host "Issue created: no"
Write-Host "Comment created: no"
Write-Host "Fork created: no"
Write-Host "Pull request created: no"
Write-Host "State:" $StatePath
Write-Host "Report:" $ReportPath
