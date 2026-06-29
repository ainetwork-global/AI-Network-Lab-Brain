param(
  [string]$BrainRoot = "$env:USERPROFILE\AI-Network-Lab-Brain"
)

Set-Location $BrainRoot

$GeneratedDir = ".\99_BRAIN_OS\generated"
New-Item -ItemType Directory -Force $GeneratedDir | Out-Null

$MarkdownFiles = Get-ChildItem -Path $BrainRoot -Recurse -File -Filter "*.md" |
  Where-Object {
    $_.FullName -notmatch "\\.git\\" -and
    $_.FullName -notmatch "\\.obsidian\\"
  }

$CurrentStateFiles = Get-ChildItem ".\00_CURRENT_STATE" -File -ErrorAction SilentlyContinue

$Model = [ordered]@{
  project = "AI Network Lab"
  brain_version = "2.0"
  generated_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
  markdown_files_count = $MarkdownFiles.Count
  current_state_files_count = $CurrentStateFiles.Count
  source_of_truth = @(
    "00_CURRENT_STATE/START_HERE.md",
    "00_CURRENT_STATE/AI_READ_FIRST.md",
    "00_CURRENT_STATE/MASTER_STATE.md",
    "00_CURRENT_STATE/PROJECT_MEMORY.json",
    "00_CURRENT_STATE/NEXT_ACTION.md",
    "00_CURRENT_STATE/PROJECT_REGISTRY.md",
    "00_CURRENT_STATE/BRAIN_QUERY.md",
    "00_CURRENT_STATE/STARTUP_PROTOCOL.md"
  )
  current_phase = "Decision Engine completed; Predictive Brain Optimizer next"
  completed_systems = @(
    "Discovery Engine",
    "Economic Scoring",
    "Smart Queue",
    "GitHub Outreach",
    "Claim Portal",
    "Ownership Verification",
    "Reward Engine",
    "Context Rewards",
    "UCB Optimizer",
    "Decision Engine",
    "Automatic Follow-up",
    "GitHub Issue Closing",
    "Brain OS v2"
  )
  next_objective = "Predictive Decision Engine / Brain Optimizer"
}

$Model | ConvertTo-Json -Depth 10 | Set-Content ".\99_BRAIN_OS\generated\knowledge_model.json" -Encoding UTF8

Write-Host "Knowledge model generated."
Write-Host "Output: 99_BRAIN_OS\generated\knowledge_model.json"
