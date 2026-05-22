# AI智能网络故障分析平台 - 开发环境统一启动脚本
[CmdletBinding()]
param(
    [string]$BackendHost = "0.0.0.0",
    [int]$BackendPort = 8000,
    [string]$FrontendHost = "0.0.0.0",
    [int]$FrontendPort = 5173,
    [int]$BackendTimeoutSeconds = 90,
    [switch]$SkipFrontendInstall
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$FrontendPath = Join-Path $ProjectRoot "frontend"
$LogsPath = Join-Path $ProjectRoot "logs"
$DevelopmentInternalApiToken = $null

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function ConvertTo-PowerShellLiteral {
    param([string]$Value)
    return "'" + ($Value -replace "'", "''") + "'"
}

function Get-HealthHost {
    param([string]$HostAddress)

    if ($HostAddress -eq "0.0.0.0" -or $HostAddress -eq "::" -or $HostAddress -eq "[::]") {
        return "127.0.0.1"
    }

    return $HostAddress
}

function Ensure-Command {
    param(
        [string]$Name,
        [string]$InstallHint
    )

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "缺少命令 $Name。$InstallHint"
    }
}

function Ensure-ProjectLayout {
    if (-not (Test-Path -LiteralPath $BackendPath)) {
        throw "后端目录不存在: $BackendPath"
    }

    if (-not (Test-Path -LiteralPath $FrontendPath)) {
        throw "前端目录不存在: $FrontendPath"
    }

    if (-not (Test-Path -LiteralPath (Join-Path $BackendPath ".env"))) {
        throw "缺少 backend/.env，请先从 backend/.env.example 复制并填写配置。"
    }

    foreach ($dir in @("app", "access", "error", "backend", "frontend")) {
        $path = Join-Path $LogsPath $dir
        if (-not (Test-Path -LiteralPath $path)) {
            New-Item -ItemType Directory -Path $path -Force | Out-Null
        }
    }
}

function Test-InvalidInternalApiToken {
    param([AllowNull()][string]$Token)

    $normalized = if ($null -eq $Token) { "" } else { $Token.Trim().ToLowerInvariant() }
    return [string]::IsNullOrWhiteSpace($normalized) -or $normalized -in @(
        "change-me",
        "change-me-internal-api-token",
        "your-token",
        "test-token"
    )
}

function New-UrlSafeToken {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
    } finally {
        $rng.Dispose()
    }

    return [Convert]::ToBase64String($bytes).TrimEnd("=").Replace("+", "-").Replace("/", "_")
}

function Get-EnvFileValue {
    param([string]$Name)

    $envPath = Join-Path $BackendPath ".env"
    foreach ($line in Get-Content -Path $envPath) {
        if ($line -match "^\s*$([regex]::Escape($Name))\s*=\s*(.*)\s*$") {
            return $Matches[1].Trim().Trim('"').Trim("'")
        }
    }

    return $null
}

function Get-DevelopmentInternalApiToken {
    $configuredToken = Get-EnvFileValue -Name "INTERNAL_API_TOKEN"
    if (-not (Test-InvalidInternalApiToken -Token $configuredToken)) {
        return $configuredToken
    }

    Write-Host "未检测到可用 INTERNAL_API_TOKEN，已生成仅本次开发会话使用的临时 Token。" -ForegroundColor Yellow
    return New-UrlSafeToken
}

function Get-PowerShellExecutable {
    $pwsh = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($pwsh) {
        return $pwsh.Source
    }

    $powershell = Get-Command powershell -ErrorAction SilentlyContinue
    if ($powershell) {
        return $powershell.Source
    }

    throw "未找到 PowerShell 可执行文件。"
}

function Start-ManagedWindow {
    param(
        [ValidateSet("backend", "frontend")]
        [string]$Role,
        [string]$Title,
        [string]$WorkingDirectory,
        [string]$Command
    )

    $shell = Get-PowerShellExecutable
    $titleLiteral = ConvertTo-PowerShellLiteral $Title
    $workdirLiteral = ConvertTo-PowerShellLiteral $WorkingDirectory
    $windowCommand = @"
`$Host.UI.RawUI.WindowTitle = $titleLiteral
Set-Location -LiteralPath $workdirLiteral
$Command
"@

    Write-Step "弹出 $Role 窗口: $Title"
    Start-Process -FilePath $shell -ArgumentList @("-NoExit", "-NoProfile", "-Command", $windowCommand) -WorkingDirectory $WorkingDirectory | Out-Null
}

function Wait-BackendReady {
    param(
        [string]$Url,
        [int]$TimeoutSeconds
    )

    Write-Step "等待后端健康检查: $Url"
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastError = $null

    while ((Get-Date) -lt $deadline) {
        try {
            $response = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3
            if ($response.StatusCode -ge 200 -and $response.StatusCode -lt 500) {
                Write-Host "后端已正常启动。" -ForegroundColor Green
                return
            }
        } catch {
            $lastError = $_.Exception.Message
        }

        Start-Sleep -Seconds 2
    }

    throw "后端在 $TimeoutSeconds 秒内未通过健康检查。最后错误: $lastError"
}

function New-BackendCommand {
    $hostLiteral = ConvertTo-PowerShellLiteral $BackendHost
    $tokenLiteral = ConvertTo-PowerShellLiteral $DevelopmentInternalApiToken
    return @"
`$env:APP_ENV = 'development'
`$env:API_AUTH_ENABLED = 'true'
`$env:INTERNAL_API_TOKEN = $tokenLiteral
`$env:LOG_LEVEL = 'DEBUG'
`$env:PYTHONDONTWRITEBYTECODE = '1'
Write-Host '后端开发服务启动中...' -ForegroundColor Green
uv run python run.py --host $hostLiteral --port $BackendPort --reload
"@
}

function New-FrontendCommand {
    $hostLiteral = ConvertTo-PowerShellLiteral $FrontendHost
    $tokenLiteral = ConvertTo-PowerShellLiteral $DevelopmentInternalApiToken
    $installCommand = "if (-not (Test-Path -LiteralPath 'node_modules')) { Write-Host '未检测到 node_modules，正在安装前端依赖...' -ForegroundColor Yellow; npm install }"

    if ($SkipFrontendInstall) {
        $installCommand = "Write-Host '已跳过前端依赖自动安装。' -ForegroundColor Yellow"
    }

return @"
`$env:NODE_ENV = 'development'
`$env:VITE_INTERNAL_API_TOKEN = $tokenLiteral
$installCommand
`$vite = Join-Path (Get-Location) 'node_modules\.bin\vite.cmd'
if (-not (Test-Path -LiteralPath `$vite)) { throw '未找到本地 Vite 可执行文件，请确认前端依赖安装成功。' }
Write-Host '前端开发服务启动中...' -ForegroundColor Green
& `$vite --host $hostLiteral --port $FrontendPort
"@
}

try {
    Write-Host "AI智能网络故障分析平台 - 开发环境启动" -ForegroundColor Green
    Write-Host "项目路径: $ProjectRoot"

    Ensure-ProjectLayout
    Ensure-Command -Name "uv" -InstallHint "请先安装 uv: https://github.com/astral-sh/uv"
    Ensure-Command -Name "npm" -InstallHint "请先安装 Node.js 和 npm。"
    $DevelopmentInternalApiToken = Get-DevelopmentInternalApiToken

    $healthHost = Get-HealthHost $BackendHost
    $healthUrl = "http://${healthHost}:$BackendPort/api/v1/health"

    Start-ManagedWindow -Role "backend" -Title "AI Network Backend Dev :$BackendPort" -WorkingDirectory $BackendPath -Command (New-BackendCommand)
    Wait-BackendReady -Url $healthUrl -TimeoutSeconds $BackendTimeoutSeconds
    Start-ManagedWindow -Role "frontend" -Title "AI Network Frontend Dev :$FrontendPort" -WorkingDirectory $FrontendPath -Command (New-FrontendCommand)

    Write-Host ""
    Write-Host "开发环境启动流程已完成。" -ForegroundColor Green
    Write-Host "后端: http://${healthHost}:$BackendPort"
    Write-Host "前端: http://127.0.0.1:$FrontendPort"
} catch {
    Write-Host ""
    Write-Host "启动失败: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
