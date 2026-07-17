param(
    [Parameter(Mandatory = $true)]
    [string]$GlobalBrain,

    [Parameter(Mandatory = $true)]
    [string]$RegistryPath,

    [Parameter(Mandatory = $true)]
    [string]$StatePath,

    [Parameter(Mandatory = $true)]
    [string]$ReportPath
)

$ErrorActionPreference = "Stop"

$GeneratedAt = (Get-Date).ToUniversalTime().ToString("o")

$DesiredSources = @(
    [pscustomobject]@{
        source_key = "github"
        category = "engineering_bounties"
        geographic_scope = "global"
        acquisition_method = "api"
        execution_priority = 90
    },
    [pscustomobject]@{
        source_key = "algora"
        category = "engineering_bounties"
        geographic_scope = "global"
        acquisition_method = "public_web_or_api"
        execution_priority = 85
    },
    [pscustomobject]@{
        source_key = "immunefi"
        category = "security_bounties"
        geographic_scope = "global"
        acquisition_method = "public_web"
        execution_priority = 85
    },
    [pscustomobject]@{
        source_key = "hackerone"
        category = "security_bounties"
        geographic_scope = "global"
        acquisition_method = "public_web"
        execution_priority = 80
    },
    [pscustomobject]@{
        source_key = "bugcrowd"
        category = "security_bounties"
        geographic_scope = "global"
        acquisition_method = "public_web"
        execution_priority = 80
    },
    [pscustomobject]@{
        source_key = "devpost"
        category = "competitions"
        geographic_scope = "global"
        acquisition_method = "public_web_or_api"
        execution_priority = 75
    },
    [pscustomobject]@{
        source_key = "grants_gov"
        category = "government_grants"
        geographic_scope = "united_states"
        acquisition_method = "official_api"
        execution_priority = 70
    },
    [pscustomobject]@{
        source_key = "eu_funding"
        category = "government_grants"
        geographic_scope = "europe"
        acquisition_method = "official_web_or_api"
        execution_priority = 70
    },
    [pscustomobject]@{
        source_key = "world_bank"
        category = "rfp_and_procurement"
        geographic_scope = "global"
        acquisition_method = "official_web_or_api"
        execution_priority = 70
    },
    [pscustomobject]@{
        source_key = "un_global_marketplace"
        category = "rfp_and_procurement"
        geographic_scope = "global"
        acquisition_method = "official_web"
        execution_priority = 70
    },
    [pscustomobject]@{
        source_key = "upwork"
        category = "freelance_projects"
        geographic_scope = "global"
        acquisition_method = "public_web"
        execution_priority = 65
    },
    [pscustomobject]@{
        source_key = "freelancer"
        category = "freelance_projects"
        geographic_scope = "global"
        acquisition_method = "public_web"
        execution_priority = 65
    },
    [pscustomobject]@{
        source_key = "contra"
        category = "freelance_projects"
        geographic_scope = "global"
        acquisition_method = "public_web"
        execution_priority = 60
    },
    [pscustomobject]@{
        source_key = "wellfound"
        category = "startup_contracts"
        geographic_scope = "global"
        acquisition_method = "public_web"
        execution_priority = 60
    },
    [pscustomobject]@{
        source_key = "ycombinator_jobs"
        category = "startup_contracts"
        geographic_scope = "global"
        acquisition_method = "public_web"
        execution_priority = 60
    },
    [pscustomobject]@{
        source_key = "latam_public_procurement"
        category = "rfp_and_procurement"
        geographic_scope = "latin_america"
        acquisition_method = "official_web"
        execution_priority = 60
    },
    [pscustomobject]@{
        source_key = "africa_procurement"
        category = "rfp_and_procurement"
        geographic_scope = "africa"
        acquisition_method = "official_web"
        execution_priority = 55
    },
    [pscustomobject]@{
        source_key = "asia_procurement"
        category = "rfp_and_procurement"
        geographic_scope = "asia"
        acquisition_method = "official_web"
        execution_priority = 55
    }
)

$SearchRoots = @(
    (Join-Path $GlobalBrain "01_EXECUTION"),
    (Join-Path $GlobalBrain "01_DISCOVERY"),
    (Join-Path $GlobalBrain "02_DISCOVERY"),
    $GlobalBrain
) | Where-Object {
    Test-Path $_
} | Select-Object -Unique

$AdapterFiles = @()

foreach ($Root in $SearchRoots) {
    $AdapterFiles += @(
        Get-ChildItem -Path $Root -Recurse -File -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match "(?i)(adapter|discovery|discover|source)"
        }
    )
}

$AdapterFiles = @(
    $AdapterFiles |
    Sort-Object FullName -Unique
)

$Registry = New-Object System.Collections.Generic.List[object]

foreach ($Source in $DesiredSources) {
    $Aliases = switch ($Source.source_key) {
        "grants_gov" { @("grants", "grants.gov", "official") }
        "eu_funding" { @("eu", "europe", "funding") }
        "un_global_marketplace" { @("ungm", "un_global", "united_nations") }
        "ycombinator_jobs" { @("ycombinator", "yc_jobs", "yc") }
        default { @($Source.source_key) }
    }

    $Matches = @(
        $AdapterFiles |
        Where-Object {
            $Name = $_.Name.ToLowerInvariant()

            $Matched = $false

            foreach ($Alias in $Aliases) {
                if ($Name.Contains($Alias.ToLowerInvariant())) {
                    $Matched = $true
                    break
                }
            }

            $Matched
        }
    )

    $AdapterPaths = @(
        $Matches |
        ForEach-Object {
            $_.FullName.Replace($GlobalBrain + "\", "")
        }
    )

    $Registry.Add(
        [pscustomobject]@{
            source_key = $Source.source_key
            category = $Source.category
            geographic_scope = $Source.geographic_scope
            acquisition_method = $Source.acquisition_method
            execution_priority = $Source.execution_priority
            adapter_detected = ($Matches.Count -gt 0)
            adapter_files = $AdapterPaths
            enabled = ($Matches.Count -gt 0)
            operational_status = if ($Matches.Count -gt 0) {
                "adapter_detected_requires_runtime_validation"
            }
            else {
                "adapter_missing"
            }
        }
    )
}

$ActiveSources = @(
    $Registry |
    Where-Object { $_.adapter_detected }
)

$MissingSources = @(
    $Registry |
    Where-Object { -not $_.adapter_detected }
)

$Categories = @(
    $Registry.category |
    Sort-Object -Unique
)

$Regions = @(
    $Registry.geographic_scope |
    Sort-Object -Unique
)

$RecommendedBuildQueue = @(
    $MissingSources |
    Sort-Object execution_priority -Descending |
    Select-Object -First 10
)

$OverallDecision = if ($ActiveSources.Count -ge 6) {
    "GLOBAL_DISCOVERY_FOUNDATION_READY"
}
elseif ($ActiveSources.Count -ge 3) {
    "GLOBAL_DISCOVERY_PARTIALLY_READY"
}
else {
    "GLOBAL_DISCOVERY_REQUIRES_SOURCE_EXPANSION"
}

$RecommendedNextAction = if ($MissingSources.Count -gt 0) {
    "build_highest_priority_missing_source_adapter"
}
else {
    "run_multi_source_global_discovery_cycle"
}

$RegistryState = [ordered]@{
    generated_at = $GeneratedAt
    purpose = "global_web_revenue_discovery"
    geographic_scope = "worldwide"
    github_role = "one_source_among_many"
    desired_sources_total = $DesiredSources.Count
    registry = $Registry
}

$RegistryState |
ConvertTo-Json -Depth 20 |
Set-Content -Path $RegistryPath -Encoding UTF8

$RouterState = [ordered]@{
    generated_at = $GeneratedAt
    overall_decision = $OverallDecision
    recommended_next_action = $RecommendedNextAction
    desired_sources_total = $DesiredSources.Count
    active_sources_total = $ActiveSources.Count
    missing_sources_total = $MissingSources.Count
    categories_total = $Categories.Count
    geographic_scopes_total = $Regions.Count
    active_sources = $ActiveSources
    recommended_build_queue = $RecommendedBuildQueue
    external_action_performed = $false
    opportunity_application_performed = $false
    issue_created = $false
    proposal_submitted = $false
    payment_requested = $false
}

$RouterState |
ConvertTo-Json -Depth 20 |
Set-Content -Path $StatePath -Encoding UTF8

$Report = New-Object System.Collections.Generic.List[string]

$Report.Add("# Global Discovery Router")
$Report.Add("")
$Report.Add("Gerado em: $GeneratedAt")
$Report.Add("")
$Report.Add("## Direção oficial")
$Report.Add("")
$Report.Add("O Global Revenue Brain deve buscar oportunidades de receita em toda a web mundial.")
$Report.Add("")
$Report.Add("GitHub é somente uma fonte entre várias.")
$Report.Add("")
$Report.Add("## Estado")
$Report.Add("")
$Report.Add("- Decisão: **$OverallDecision**")
$Report.Add("- Fontes desejadas: **$($DesiredSources.Count)**")
$Report.Add("- Fontes com adapter detectado: **$($ActiveSources.Count)**")
$Report.Add("- Fontes ainda sem adapter: **$($MissingSources.Count)**")
$Report.Add("- Categorias cobertas: **$($Categories.Count)**")
$Report.Add("- Escopos geográficos: **$($Regions.Count)**")
$Report.Add("- Próxima ação: **$RecommendedNextAction**")
$Report.Add("")
$Report.Add("## Fontes com adapter detectado")
$Report.Add("")

if ($ActiveSources.Count -eq 0) {
    $Report.Add("- Nenhuma.")
}
else {
    foreach ($Source in $ActiveSources) {
        $Report.Add(
            "- **$($Source.source_key)** — $($Source.category) — $($Source.geographic_scope)"
        )
    }
}

$Report.Add("")
$Report.Add("## Fila recomendada de novos adapters")
$Report.Add("")

$Position = 0

foreach ($Source in $RecommendedBuildQueue) {
    $Position++

    $Report.Add(
        "$Position. **$($Source.source_key)** — prioridade $($Source.execution_priority) — $($Source.category) — $($Source.geographic_scope)"
    )
}

$Report.Add("")
$Report.Add("## Segurança")
$Report.Add("")
$Report.Add("- Aplicação enviada: **não**")
$Report.Add("- Proposta enviada: **não**")
$Report.Add("- Issue criada: **não**")
$Report.Add("- Pagamento solicitado: **não**")
$Report.Add("- Ação externa executada: **não**")

$Report |
Set-Content -Path $ReportPath -Encoding UTF8

Write-Host ""
Write-Host "===== GLOBAL DISCOVERY ROUTER =====" -ForegroundColor Cyan
Write-Host "Overall decision:" $OverallDecision
Write-Host "Desired sources:" $DesiredSources.Count
Write-Host "Adapters detected:" $ActiveSources.Count
Write-Host "Missing adapters:" $MissingSources.Count
Write-Host "Categories:" $Categories.Count
Write-Host "Geographic scopes:" $Regions.Count
Write-Host "Recommended next action:" $RecommendedNextAction

Write-Host ""
Write-Host "===== ACTIVE GLOBAL SOURCES ====="

if ($ActiveSources.Count -eq 0) {
    Write-Host "None"
}
else {
    foreach ($Source in $ActiveSources) {
        Write-Host ""
        Write-Host "Source:" $Source.source_key
        Write-Host "Category:" $Source.category
        Write-Host "Geographic scope:" $Source.geographic_scope
        Write-Host "Adapters:" ($Source.adapter_files -join ", ")
    }
}

Write-Host ""
Write-Host "===== NEXT GLOBAL ADAPTER BUILD QUEUE ====="

$Position = 0

foreach ($Source in $RecommendedBuildQueue) {
    $Position++

    Write-Host ""
    Write-Host "$Position. $($Source.source_key)"
    Write-Host "   Priority:" $Source.execution_priority
    Write-Host "   Category:" $Source.category
    Write-Host "   Region:" $Source.geographic_scope
}

Write-Host ""
Write-Host "===== GLOBAL DISCOVERY ROUTER SAFETY =====" -ForegroundColor Cyan
Write-Host "External action performed: no"
Write-Host "Opportunity application performed: no"
Write-Host "Issue created: no"
Write-Host "Proposal submitted: no"
Write-Host "Payment requested: no"
Write-Host "Registry:" $RegistryPath
Write-Host "State:" $StatePath
Write-Host "Report:" $ReportPath
