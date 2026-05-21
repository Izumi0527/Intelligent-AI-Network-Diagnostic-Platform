# 后端运行时依赖验证：确保 uv run 会安装 run.py 启动所需包。
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
    Assert-True $match.Success "未找到 [$SectionName] 配置段"
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
    Assert-True ($ProjectSection -match "`"$([regex]::Escape($package))([=><!~\[]|`")") "运行时依赖未声明在 [project].dependencies: $package"
}

$WheelSection = Get-Section -Toml $Content -SectionName "tool.hatch.build.targets.wheel"
Assert-True (-not ($WheelSection -match "(?m)^dependencies\s*=")) "[tool.hatch.build.targets.wheel] 不应声明 dependencies，运行时依赖应放在 [project].dependencies"

Write-Host "后端运行时依赖声明验证通过" -ForegroundColor Green
