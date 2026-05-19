# Sync Mailchimp contacts, then print a Codex prompt you can paste.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$Python = $null
$Candidates = @(
    (Join-Path $Root ".venv\Scripts\python.exe"),
    (Join-Path $Root "venv\Scripts\python.exe")
)

foreach ($Candidate in $Candidates) {
    if (Test-Path $Candidate) {
        $Python = $Candidate
        break
    }
}

if (-not $Python) {
    $PyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($PyLauncher) {
        $Python = "py"
    }
}

if (-not $Python) {
    Write-Host "Python not found. Install from https://www.python.org/downloads/ or run:" -ForegroundColor Red
    Write-Host '  py scripts/sync_mailchimp.py --only-new' -ForegroundColor Yellow
    exit 1
}

if ($Python -eq "py") {
    & py scripts/sync_mailchimp.py --only-new
} else {
    & $Python scripts/sync_mailchimp.py --only-new
}

if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host ""
Write-Host "Paste into Codex:" -ForegroundColor Cyan
Write-Host @"
Read data/mvp/submissions.csv. For each row with status=new and empty processed_at, run the artist opportunity workflow and produce a draft shortlist. Mark rows processed when done.
"@
