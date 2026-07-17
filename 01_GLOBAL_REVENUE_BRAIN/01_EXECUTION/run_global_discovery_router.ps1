param(
    [string]$BrainRoot = "C:\Users\AP10\AI-Network-Lab-Brain"
)

$ErrorActionPreference = "Stop"

$GlobalBrain = Join-Path $BrainRoot "01_GLOBAL_REVENUE_BRAIN"

$RouterPath = Join-Path `
    $GlobalBrain `
    "01_EXECUTION\global_discovery_router.ps1"

$RegistryPath = Join-Path `
    $GlobalBrain `
    "00_CURRENT_STATE\GLOBAL_SOURCE_REGISTRY.json"

$StatePath = Join-Path `
    $GlobalBrain `
    "00_CURRENT_STATE\GLOBAL_DISCOVERY_ROUTER_STATE.json"

$ReportPath = Join-Path `
    $GlobalBrain `
    "12_REPORTS\LATEST_GLOBAL_DISCOVERY_ROUTER.md"

& powershell.exe `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File $RouterPath `
    -GlobalBrain $GlobalBrain `
    -RegistryPath $RegistryPath `
    -StatePath $StatePath `
    -ReportPath $ReportPath

exit $LASTEXITCODE
