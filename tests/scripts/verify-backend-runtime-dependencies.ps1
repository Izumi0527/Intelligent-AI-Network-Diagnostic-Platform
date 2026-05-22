# Static check for backend runtime dependencies used by uv run python run.py.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$PyprojectPath = Join-Path $ProjectRoot "backend/pyproject.toml"
$Content = Get-Content -Path $PyprojectPath -Raw

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Get-Section {
    param(
        [string]$Toml,
        [string]$SectionName
    )

    $pattern = "(?ms)^\[$([regex]::Escape($SectionName))\]\s*(.*?)(?=^\[|\z)"
    $match = [regex]::Match($Toml, $pattern)
    Assert-True $match.Success "Missing [$SectionName] section"
    return $match.Groups[1].Value
}

$ProjectSection = Get-Section -Toml $Content -SectionName "project"
$RuntimePackages = @(
    "fastapi",
    "uvicorn",
    "pydantic",
    "pydantic-settings",
    "sse-starlette",
    "netmiko",
    "aiohttp",
    "python-dotenv",
    "httpx",
    "paramiko",
    "python-jose",
    "passlib",
    "bcrypt",
    "requests"
)

foreach ($package in $RuntimePackages) {
    $escapedPackage = [regex]::Escape($package)
    Assert-True ($ProjectSection -match "`"$escapedPackage([=><!~\[]|`")") "Missing runtime dependency in [project].dependencies: $package"
}

$WheelSection = Get-Section -Toml $Content -SectionName "tool.hatch.build.targets.wheel"
Assert-True (-not ($WheelSection -match "(?m)^dependencies\s*=")) "[tool.hatch.build.targets.wheel] must not declare dependencies"

Write-Host "Backend runtime dependency verification passed" -ForegroundColor Green
