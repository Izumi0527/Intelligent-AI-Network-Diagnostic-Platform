# Backend quality gate: dependencies, lint, focused tests, and script contracts.
[CmdletBinding()]
param(
    [string[]]$PytestTargets = @(
        "tests/test_backend_package_metadata.py",
        "tests/test_architecture_boundaries.py",
        "tests/test_pytest_cache_config.py",
        "tests/test_run_startup_config.py",
        "tests/test_pydantic_v2_models.py",
        "tests/test_backend_security_and_connection_policy.py",
        "tests/test_terminal_connection_regressions.py",
        "tests/test_telnet_login_policy.py"
    )
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$PythonPath = Join-Path $BackendPath ".venv/Scripts/python.exe"

$RuffTargets = @(
    "backend/run.py",
    "backend/app/config/settings.py",
    "backend/app/api/deps.py",
    "backend/app/main.py",
    "backend/app/core/rate_limit.py",
    "backend/app/core/network/telnet/client.py",
    "backend/app/core/network/telnet/connection.py",
    "backend/app/core/network/telnet/devices/huawei.py",
    "backend/app/models/ai.py",
    "backend/app/models/terminal.py",
    "backend/app/models/network.py",
    "backend/app/services/terminal_service.py",
    "backend/app/services/terminal_exceptions.py",
    "backend/app/services/ai/base.py",
    "backend/app/services/ai/application_service.py",
    "backend/app/utils/logger.py",
    "backend/app/utils/terminal_policy.py",
    "tests/test_backend_package_metadata.py",
    "tests/test_architecture_boundaries.py",
    "tests/test_pytest_cache_config.py",
    "tests/test_run_startup_config.py",
    "tests/test_pydantic_v2_models.py",
    "tests/test_telnet_login_policy.py"
)

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Invoke-Native {
    param(
        [string]$FilePath,
        [string[]]$Arguments,
        [string]$WorkingDirectory = $ProjectRoot
    )

    $emptyInput = New-TemporaryFile
    try {
        $process = Start-Process `
            -FilePath $FilePath `
            -ArgumentList $Arguments `
            -WorkingDirectory $WorkingDirectory `
            -RedirectStandardInput $emptyInput.FullName `
            -Wait `
            -PassThru
    } finally {
        Remove-Item -LiteralPath $emptyInput.FullName -Force -ErrorAction SilentlyContinue
    }

    if ($process.ExitCode -ne 0) {
        throw "Command failed: $FilePath $($Arguments -join ' ')"
    }
}

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Missing backend virtualenv Python: $PythonPath"
}

Write-Step "Run uv pip check"
Invoke-Native -FilePath "uv" -Arguments @("pip", "check") -WorkingDirectory $BackendPath

Write-Step "Run backend dependency metadata verification"
& (Join-Path $ProjectRoot "tests/scripts/verify-backend-runtime-dependencies.ps1")

Write-Step "Run focused backend ruff check"
Invoke-Native -FilePath $PythonPath -Arguments (@("-m", "ruff", "check") + $RuffTargets)

Write-Step "Run focused backend pytest"
Invoke-Native -FilePath $PythonPath -Arguments (
    @("-m", "pytest") + $PytestTargets + @("-q", "--no-cov", "-p", "no:cacheprovider")
)

Write-Step "Run launch script contract verification"
& (Join-Path $ProjectRoot "tests/scripts/verify-launch-scripts.ps1")

Write-Host "Backend quality checks passed." -ForegroundColor Green
