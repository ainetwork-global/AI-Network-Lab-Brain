param(
    [string]$BrainRoot="$env:USERPROFILE\AI-Network-Lab-Brain"
)

Set-Location $BrainRoot

$Output=".\99_BRAIN_OS\generated\brain_inventory.json"

$Inventory=[ordered]@{
    generated_at=(Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
    markdown_files=@()
    folders=@()
}

Get-ChildItem $BrainRoot -Directory |
Where-Object{
    $_.Name -notin @(".git",".obsidian","99_BRAIN_OS")
} |
ForEach-Object{

    $Inventory.folders+=$_.Name

}

Get-ChildItem $BrainRoot -Recurse -Filter *.md -File |
Where-Object{
    $_.FullName -notmatch "\\.git\\" -and
    $_.FullName -notmatch "\\99_BRAIN_OS\\generated\\"
} |
ForEach-Object{

    $Text=Get-Content $_.FullName -Raw

    $Inventory.markdown_files+=[ordered]@{

        file=$_.FullName.Replace($BrainRoot+"\","")

        title=([regex]::Match($Text,"(?m)^# (.+)$").Groups[1].Value)

        components=([regex]::Matches($Text,"(?i)(Decision Engine|Discovery Engine|Billing|Marketplace|Claim|Reward Engine|UCB|Worker|Edge Function|Runtime|Stripe|Supabase)") |
            ForEach-Object{$_.Value} |
            Sort-Object -Unique)

        urls=([regex]::Matches($Text,"https?://\S+") |
            ForEach-Object{$_.Value} |
            Sort-Object -Unique)

    }

}

$Inventory |
ConvertTo-Json -Depth 10 |
Set-Content $Output -Encoding UTF8

Write-Host ""
Write-Host "Brain Inventory generated."
Write-Host ""
Write-Host $Output
