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

# Adapter detection must use real source-code evidence.
# Never infer adapters from .venv, __pycache__, reports, logs,
# generated CSV files, backups, or generic filename fragments.

$AdapterEvidenceRules = @{
    github = @(
        @{
            relative_path = "02_DISCOVERY\global_paid_work_discovery.py"
            required_markers = @(
                "api.github.com",
                "fetch_github_paid_issues"
            )
        }
    )

    algora = @(
        @{
            relative_path = "02_DISCOVERY\algora_open_bounty_adapter.py"
            required_markers = @(
                "algora"
            )
        }
    )

    immunefi = @(
        @{
            relative_path = "02_DISCOVERY\official_source_adapters.py"
            required_markers = @(
                "IMMUNEFI_LISTING",
                "scan_immunefi"
            )
        }
    )

    devpost = @(
        @{
            relative_path = "02_DISCOVERY\devpost_official_adapter.py"
            required_markers = @(
                "devpost"
            )
        }
    )

    grants_gov = @(
        @{
            relative_path = "02_DISCOVERY\official_source_adapters.py"
            required_markers = @(
                "api.grants.gov",
                "scan_grants"
            )
        }
    )

    hackerone = @(
        @{
            relative_path = "02_DISCOVERY\hackerone_adapter.py"
            required_markers = @(
                "hackerone"
            )
        }
    )

    bugcrowd = @(
        @{
            relative_path = "02_DISCOVERY\bugcrowd_adapter.py"
            required_markers = @(
                "bugcrowd"
            )
        }
    )

    eu_funding = @(
        @{
            relative_path = "02_DISCOVERY\eu_funding_adapter.py"
            required_markers = @(
                "eu_funding"
            )
        }
    )

    world_bank = @(
        @{
            relative_path = "02_DISCOVERY\world_bank_adapter.py"
            required_markers = @(
                "world_bank"
            )
        }
    )

    un_global_marketplace = @(
        @{
            relative_path = "02_DISCOVERY\un_global_marketplace_adapter.py"
            required_markers = @(
                "ungm"
            )
        }
    )

    upwork = @(
        @{
            relative_path = "02_DISCOVERY\upwork_adapter.py"
            required_markers = @(
                "upwork"
            )
        }
    )

    freelancer = @(
        @{
            relative_path = "02_DISCOVERY\freelancer_adapter.py"
            required_markers = @(
                "freelancer"
            )
        }
    )

    contra = @(
        @{
            relative_path = "02_DISCOVERY\contra_adapter.py"
            required_markers = @(
                "contra"
            )
        }
    )

    wellfound = @(
        @{
            relative_path = "02_DISCOVERY\wellfound_adapter.py"
            required_markers = @(
                "wellfound"
            )
        }
    )

    ycombinator_jobs = @(
        @{
            relative_path = "02_DISCOVERY\ycombinator_jobs_adapter.py"
            required_markers = @(
                "ycombinator",
                "jobs"
            )
        }
    )

    latam_public_procurement = @(
        @{
            relative_path = "02_DISCOVERY\latam_public_procurement_adapter.py"
            required_markers = @(
                "latam_public_procurement"
            )
        }
    )

    africa_procurement = @(
        @{
            relative_path = "02_DISCOVERY\africa_procurement_adapter.py"
            required_markers = @(
                "africa_procurement"
            )
        }
    )

    asia_procurement = @(
        @{
            relative_path = "02_DISCOVERY\asia_procurement_adapter.py"
            required_markers = @(
                "asia_procurement"
            )
        }
    )
}

function Test-AdapterEvidence {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RelativePath,

        [Parameter(Mandatory = $true)]
        [string[]]$RequiredMarkers
    )

    $FullPath = Join-Path $GlobalBrain $RelativePath

    if (-not (Test-Path $FullPath -PathType Leaf)) {
        return $false
    }

    $Extension = [System.IO.Path]::GetExtension($FullPath).ToLowerInvariant()

    if ($Extension -notin @(".py", ".ps1", ".js", ".ts")) {
        return $false
    }

    $Content = Get-Content $FullPath -Raw -Encoding UTF8

    foreach ($Marker in $RequiredMarkers) {
        if ($Content.IndexOf(
                $Marker,
                [System.StringComparison]::OrdinalIgnoreCase
            ) -lt 0) {
            return $false
        }
    }

    return $true
}

$Registry = New-Object System.Collections.Generic.List[object]

foreach ($Source in $DesiredSources) {
    $EvidenceFiles = New-Object System.Collections.Generic.List[string]
    $Rules = @($AdapterEvidenceRules[$Source.source_key])

    foreach ($Rule in $Rules) {
        if ($null -eq $Rule) {
            continue
        }

        $RelativePath = [string]$Rule.relative_path
        $Markers = @($Rule.required_markers)

        if (Test-AdapterEvidence `
                -RelativePath $RelativePath `
                -RequiredMarkers $Markers) {
            $EvidenceFiles.Add($RelativePath)
        }
    }

    $AdapterDetected = $EvidenceFiles.Count -gt 0

    $Registry.Add(
        [pscustomobject]@{
            source_key = $Source.source_key
            category = $Source.category
            geographic_scope = $Source.geographic_scope
            acquisition_method = $Source.acquisition_method
            execution_priority = $Source.execution_priority
            adapter_detected = $AdapterDetected
            adapter_files = @($EvidenceFiles)
            enabled = $AdapterDetected
            operational_status = if ($AdapterDetected) {
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

