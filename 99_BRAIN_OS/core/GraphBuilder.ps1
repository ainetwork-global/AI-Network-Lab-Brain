param(
    [string]$BrainRoot="$env:USERPROFILE\AI-Network-Lab-Brain"
)

Set-Location $BrainRoot

$Output=".\99_BRAIN_OS\generated\knowledge_graph.json"

$Folders=Get-ChildItem $BrainRoot -Directory |
Where-Object{
    $_.Name -notin @(".git",".obsidian","99_BRAIN_OS")
}

$Graph=@()

foreach($Folder in $Folders){

    $Files=Get-ChildItem $Folder.FullName -Filter *.md -File -ErrorAction SilentlyContinue

    $Node=[ordered]@{
        component=$Folder.Name
        markdown_files=$Files.Count
        files=@()
    }

    foreach($File in $Files){

        $Node.files+=[ordered]@{
            name=$File.Name
            relative=$File.FullName.Replace($BrainRoot+"\","")
        }

    }

    $Graph+=$Node

}

$Graph |
ConvertTo-Json -Depth 8 |
Set-Content $Output -Encoding UTF8

Write-Host ""
Write-Host "Knowledge Graph generated."
Write-Host ""
Write-Host $Output
