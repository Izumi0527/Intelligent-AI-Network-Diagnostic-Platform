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
    return @"
`$env:APP_ENV = 'development'
`$env:LOG_LEVEL = 'DEBUG'
`$env:PYTHONDONTWRITEBYTECODE = '1'
Write-Host '后端开发服务启动中...' -ForegroundColor Green
uv run python run.py --host $hostLiteral --port $BackendPort --reload
"@
}

function New-FrontendCommand {
    $hostLiteral = ConvertTo-PowerShellLiteral $FrontendHost
    $installCommand = "if (-not (Test-Path -LiteralPath 'node_modules')) { Write-Host '未检测到 node_modules，正在安装前端依赖...' -ForegroundColor Yellow; npm install }"

    if ($SkipFrontendInstall) {
        $installCommand = "Write-Host '已跳过前端依赖自动安装。' -ForegroundColor Yellow"
    }

    return @"
`$env:NODE_ENV = 'development'
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
