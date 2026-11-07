param(
    [string]$UpstreamUrl = "https://github.com/Vimaladharsan/TrustShare-Encrypted-File-Sharing-Collaboration-Platform.git",
    [string]$Branch = "trustshare-complete"
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Get-Location).Path
$GitDir = Join-Path $RepoRoot ".git"

if (-not (Test-Path $GitDir)) {
    throw "Run this script from the root of your cloned mythribanda/TrustShare repository."
}

$Remote = git remote get-url origin
if ($LASTEXITCODE -ne 0 -or $Remote -notmatch "mythribanda/TrustShare") {
    throw "The origin remote must point to https://github.com/mythribanda/TrustShare.git."
}

git switch $Branch
if ($LASTEXITCODE -ne 0) {
    throw "Could not switch to branch $Branch."
}

$Status = git status --porcelain
if ($Status) {
    throw "Your working tree has uncommitted changes. Commit or stash them before importing so nothing is lost."
}

$Email = git config user.email
if (-not $Email) {
    $Email = Read-Host "Enter the email address verified on your GitHub account"
    if (-not $Email) { throw "A GitHub-verified commit email is required." }
    git config user.email $Email
}
git config user.name "Mythri Raj Banda"

$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("trustshare-upstream-" + [guid]::NewGuid().ToString("N"))
$Source = Join-Path $TempRoot "source"

try {
    New-Item -ItemType Directory -Path $TempRoot | Out-Null
    git clone --depth 1 --branch main $UpstreamUrl $Source
    if ($LASTEXITCODE -ne 0) { throw "Could not download the upstream main branch." }

    robocopy $Source $RepoRoot /E /XD ".git" "node_modules" ".venv" "__pycache__" ".pytest_cache" /XF ".env"
    $CopyExit = $LASTEXITCODE
    if ($CopyExit -ge 8) { throw "File copy failed with robocopy exit code $CopyExit." }

    git add -A
    if ($LASTEXITCODE -ne 0) { throw "Git could not stage the imported files." }

    git commit -m "Import complete TrustShare implementation with upstream MIT attribution"
    if ($LASTEXITCODE -ne 0) { throw "Git commit failed. Review the output and repository status." }

    git push origin $Branch
    if ($LASTEXITCODE -ne 0) { throw "Push failed. The import commit exists locally; resolve authentication or push errors and retry git push origin $Branch." }

    Write-Host ""
    Write-Host "Import pushed successfully to mythribanda/TrustShare branch $Branch."
    Write-Host "The upstream LICENSE and source attribution files were copied with the project."
}
finally {
    if (Test-Path $TempRoot) {
        Remove-Item $TempRoot -Recurse -Force
    }
}
