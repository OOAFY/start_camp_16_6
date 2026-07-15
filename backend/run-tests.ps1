param(
    [switch]$Watch,
    [switch]$HealthOnly,
    [switch]$PostsOnly
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:PYTHONPATH = (Resolve-Path "..").Path

function Invoke-TestCommand {
    param(
        [string]$Name,
        [string[]]$CommandArgs
    )

    Write-Host ""
    Write-Host "==> $Name" -ForegroundColor Cyan
    & py -3 @CommandArgs
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

if ($HealthOnly) {
    Invoke-TestCommand -Name "backend health tests" -CommandArgs @("-m", "pytest", "tests/test_health.py")
    exit 0
}

if ($PostsOnly) {
    Invoke-TestCommand -Name "backend post tests" -CommandArgs @("-m", "pytest", "tests/test_posts.py")
    exit 0
}

Invoke-TestCommand -Name "db session tests" -CommandArgs @("-m", "pytest", "tests/test_db_session.py")
Invoke-TestCommand -Name "health tests" -CommandArgs @("-m", "pytest", "tests/test_health.py")
Invoke-TestCommand -Name "post tests" -CommandArgs @("-m", "pytest", "tests/test_posts.py")
Invoke-TestCommand -Name "integration API tests" -CommandArgs @("-m", "pytest", "tests/test_integration_apis.py")
Invoke-TestCommand -Name "festival API tests" -CommandArgs @("-m", "pytest", "tests/test_festivals.py")

Write-Host ""
Write-Host "All backend tests passed." -ForegroundColor Green
