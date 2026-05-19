$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$LogDir = Join-Path $Root "outputs"
if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir | Out-Null
}
$LogFile = Join-Path $LogDir "sync_then_process.log"

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
    "[$(Get-Date -Format s)] Python not found." | Out-File -FilePath $LogFile -Append -Encoding utf8
    exit 1
}

function Invoke-Step {
    param(
        [string]$Label,
        [string[]]$Arguments
    )

    "[$(Get-Date -Format s)] START $Label" | Out-File -FilePath $LogFile -Append -Encoding utf8
    if ($Python -eq "py") {
        & py @Arguments 2>&1 | Out-File -FilePath $LogFile -Append -Encoding utf8
    } else {
        & $Python @Arguments 2>&1 | Out-File -FilePath $LogFile -Append -Encoding utf8
    }
    $ExitCode = $LASTEXITCODE
    "[$(Get-Date -Format s)] END $Label exit=$ExitCode" | Out-File -FilePath $LogFile -Append -Encoding utf8
    if ($ExitCode -ne 0) {
        exit $ExitCode
    }
}

Invoke-Step -Label "sync_mailchimp" -Arguments @("scripts/sync_mailchimp.py", "--only-new")
"[$(Get-Date -Format s)] INFO New submissions are queued as research_pending. The research runner will process research_pending rows and only emailed_ready rows can be sent." | Out-File -FilePath $LogFile -Append -Encoding utf8
Invoke-Step -Label "run_research_pipeline" -Arguments @("scripts/run_research_pipeline.py")
Invoke-Step -Label "send_result_emails" -Arguments @("scripts/send_result_emails.py")
exit 0
