[CmdletBinding()]
param(
    [switch]$Stop
)

$ErrorActionPreference = "Stop"

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$FrontendDir = Join-Path $RepoRoot "frontend"
$BackendDir = Join-Path $RepoRoot "backend"
$RuntimeDir = Join-Path $RepoRoot ".local"
$BackendPidFile = Join-Path $RuntimeDir "backend.pid"
$FrontendPidFile = Join-Path $RuntimeDir "frontend.pid"

function Get-ListeningProcessIds {
    param([int]$Port)

    $Ids = @(
        Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue |
            Select-Object -ExpandProperty OwningProcess -Unique
    )
    if ($Ids) {
        return $Ids
    }

    $Pattern = "^\s*TCP\s+\S+:$Port\s+\S+\s+LISTENING\s+(\d+)\s*$"
    return @(
        & netstat.exe -ano -p TCP |
            ForEach-Object { if ($_ -match $Pattern) { [int]$Matches[1] } } |
            Sort-Object -Unique
    )
}

function Stop-ManagedProcess {
    param(
        [string]$Name,
        [string]$PidFile,
        [int]$Port
    )

    $ProcessIds = @()
    if (Test-Path -LiteralPath $PidFile) {
        $ProcessIds = @(Get-Content -LiteralPath $PidFile | ForEach-Object { [int]$_ })
    } else {
        # A healthy server may have been running before this script and reused.
        $ProcessIds = @(Get-ListeningProcessIds -Port $Port)
    }

    if (-not $ProcessIds) {
        Write-Host "$Name server is already stopped."
    }

    foreach ($ProcessId in $ProcessIds) {
        # Stop child processes created by the development server as well.
        $PreviousErrorActionPreference = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $TaskkillOutput = & taskkill.exe /PID $ProcessId /T /F 2>&1
        $TaskkillExitCode = $LASTEXITCODE
        $ErrorActionPreference = $PreviousErrorActionPreference
        if ($TaskkillExitCode -eq 0) {
            Write-Host "$Name server stopped. (PID: $ProcessId)"
        } else {
            Write-Warning "$Name PID $ProcessId could not be stopped: $TaskkillOutput"
        }
    }

    if (Test-Path -LiteralPath $PidFile) {
        Remove-Item -LiteralPath $PidFile -Force
    }
}

if ($Stop) {
    Stop-ManagedProcess -Name "frontend" -PidFile $FrontendPidFile -Port 5173
    Stop-ManagedProcess -Name "backend" -PidFile $BackendPidFile -Port 8000
    exit 0
}

foreach ($CommandName in @("python", "npm")) {
    if (-not (Get-Command $CommandName -ErrorAction SilentlyContinue)) {
        throw "Required command '$CommandName' was not found. Check PATH."
    }
}

$EnvFile = Join-Path $RepoRoot ".env"
if (-not (Test-Path -LiteralPath $EnvFile)) {
    throw ".env was not found. Create it in the repository root using .env.example."
}

$HasOpenAIKey = Get-Content -LiteralPath $EnvFile | Where-Object {
    $_ -match '^\s*OPENAI_API_KEY\s*=\s*[^\s#]+'
}
if (-not $HasOpenAIKey) {
    Write-Warning "OPENAI_API_KEY is empty, so chatbot requests will fail."
}

if (-not (Test-Path -LiteralPath (Join-Path $FrontendDir "node_modules"))) {
    throw "frontend/node_modules was not found. Run 'npm install' in frontend first."
}

function Test-Url {
    param([string]$Url)

    try {
        $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
        return $Response.StatusCode -ge 200 -and $Response.StatusCode -lt 400
    } catch {
        return $false
    }
}

New-Item -ItemType Directory -Path $RuntimeDir -Force | Out-Null

$BackendOutLog = Join-Path $RuntimeDir "backend.out.log"
$BackendErrorLog = Join-Path $RuntimeDir "backend.error.log"
$FrontendOutLog = Join-Path $RuntimeDir "frontend.out.log"
$FrontendErrorLog = Join-Path $RuntimeDir "frontend.error.log"

$BackendUrl = "http://127.0.0.1:8000/api/health"
$FrontendUrl = "http://localhost:5173/"

if (Test-Url $BackendUrl) {
    Write-Host "backend is already running and will be reused."
    $BackendProcessIds = @(Get-ListeningProcessIds -Port 8000)
    if ($BackendProcessIds) {
        $BackendProcessIds | Set-Content -LiteralPath $BackendPidFile
    }
} else {
    if (Get-ListeningProcessIds -Port 8000) {
        throw "Port 8000 is occupied by a non-LocalHub server."
    }

    $env:PYTHONPATH = "$RepoRoot;$BackendDir"
    $BackendProcess = Start-Process `
        -FilePath (Get-Command python).Source `
        -ArgumentList @("-m", "uvicorn", "app.main:app", "--app-dir", "backend", "--host", "127.0.0.1", "--port", "8000", "--reload") `
        -WorkingDirectory $RepoRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $BackendOutLog `
        -RedirectStandardError $BackendErrorLog `
        -PassThru
    $BackendProcess.Id | Set-Content -LiteralPath $BackendPidFile
}

if (Test-Url $FrontendUrl) {
    Write-Host "frontend is already running and will be reused."
    $FrontendProcessIds = @(Get-ListeningProcessIds -Port 5173)
    if ($FrontendProcessIds) {
        $FrontendProcessIds | Set-Content -LiteralPath $FrontendPidFile
    }
} else {
    if (Get-ListeningProcessIds -Port 5173) {
        throw "Port 5173 is occupied by a non-LocalHub server."
    }

    $env:VITE_API_BASE_URL = "http://localhost:8000/api"
    $NpmCommand = (Get-Command npm.cmd).Source
    $FrontendProcess = Start-Process `
        -FilePath $NpmCommand `
        -ArgumentList @("run", "dev", "--", "--host", "localhost", "--strictPort") `
        -WorkingDirectory $FrontendDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $FrontendOutLog `
        -RedirectStandardError $FrontendErrorLog `
        -PassThru
    $FrontendProcess.Id | Set-Content -LiteralPath $FrontendPidFile
}

function Wait-ForUrl {
    param(
        [string]$Name,
        [string]$Url
    )

    for ($Attempt = 1; $Attempt -le 30; $Attempt++) {
        try {
            $Response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2
            if ($Response.StatusCode -ge 200 -and $Response.StatusCode -lt 400) {
                Write-Host "$Name is ready: $Url"
                return
            }
        } catch {
            Start-Sleep -Milliseconds 500
        }
    }

    throw "$Name did not start in time. Check the .local logs."
}

try {
    Wait-ForUrl -Name "backend" -Url $BackendUrl
    Wait-ForUrl -Name "frontend" -Url $FrontendUrl
} catch {
    Write-Host "Backend error log: $BackendErrorLog"
    Write-Host "Frontend error log: $FrontendErrorLog"
    throw
}

Write-Host ""
Write-Host "LocalHub development servers are running."
Write-Host "FE:   http://localhost:5173/"
Write-Host "API:  http://localhost:8000/docs"
Write-Host "LOG:  $RuntimeDir"
Write-Host "Stop: .\scripts\local-dev.ps1 -Stop"
