param(
  [string]$Command = "help",
  [string]$Query = ""
)

$BrainRoot = "$env:USERPROFILE\AI-Network-Lab-Brain"
Set-Location $BrainRoot

function Show-Help {
  Write-Host ""
  Write-Host "AI Network Lab Brain OS CLI"
  Write-Host "==========================="
  Write-Host ""
  Write-Host "Comandos disponíveis:"
  Write-Host ""
  Write-Host "  build   - Reconstrói índices automáticos do Brain"
  Write-Host "  status  - Mostra status rápido do Brain"
  Write-Host "  help    - Mostra esta ajuda"
  Write-Host ""
  Write-Host "Exemplos:"
  Write-Host ""
  Write-Host "  powershell -ExecutionPolicy Bypass -File .\99_BRAIN_OS\Brain.ps1 build"
  Write-Host "  powershell -ExecutionPolicy Bypass -File .\99_BRAIN_OS\Brain.ps1 status"
  Write-Host ""
}

function Run-Build {
  Write-Host "Executando Brain build..."
  powershell -ExecutionPolicy Bypass -File ".\99_BRAIN_OS\BUILD_BRAIN.ps1"
}

function Show-Status {
  $MarkdownFiles = Get-ChildItem -Path $BrainRoot -Recurse -File -Filter "*.md" |
    Where-Object {
      $_.FullName -notmatch "\\.git\\" -and
      $_.FullName -notmatch "\\.obsidian\\"
    }

  $CurrentStateFiles = Get-ChildItem -Path ".\00_CURRENT_STATE" -File -ErrorAction SilentlyContinue

  Write-Host ""
  Write-Host "AI Network Lab Brain Status"
  Write-Host "==========================="
  Write-Host ""
  Write-Host "Brain root: $BrainRoot"
  Write-Host "Markdown files: $($MarkdownFiles.Count)"
  Write-Host "Current State files: $($CurrentStateFiles.Count)"
  Write-Host ""
  Write-Host "Arquivos vivos principais:"
  Write-Host ""
  Write-Host "  START_HERE.md:        $(Test-Path '.\00_CURRENT_STATE\START_HERE.md')"
  Write-Host "  AI_READ_FIRST.md:     $(Test-Path '.\00_CURRENT_STATE\AI_READ_FIRST.md')"
  Write-Host "  MASTER_STATE.md:      $(Test-Path '.\00_CURRENT_STATE\MASTER_STATE.md')"
  Write-Host "  PROJECT_MEMORY.json:  $(Test-Path '.\00_CURRENT_STATE\PROJECT_MEMORY.json')"
  Write-Host "  NEXT_ACTION.md:       $(Test-Path '.\00_CURRENT_STATE\NEXT_ACTION.md')"
  Write-Host "  SYSTEM_MAP.md:        $(Test-Path '.\00_CURRENT_STATE\SYSTEM_MAP.md')"
  Write-Host ""
}

switch ($Command.ToLower()) {
  "build"  { Run-Build }
  "status" { Show-Status }
  "help"   { Show-Help }
  default  { Show-Help }
}
