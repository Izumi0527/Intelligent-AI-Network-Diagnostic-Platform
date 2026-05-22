# AI智能网络故障分析平台 - 前端 lint + typecheck 检查脚本
[CmdletBinding()]
param(
    [switch]$Fix
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendPath = Join-Path $ProjectRoot "frontend"

function Write-Step {
    param([string]$Message)
    Write-Host "==> $Message" -ForegroundColor Cyan
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

try {
    if (-not (Test-Path -LiteralPath $FrontendPath)) {
        throw "前端目录不存在: $FrontendPath"
    }

    Ensure-Command -Name "npm" -InstallHint "请先安装 Node.js 和 npm。"

    Push-Location -LiteralPath $FrontendPath
    try {
        if (-not (Test-Path -LiteralPath "node_modules")) {
            Write-Step "未检测到 node_modules，正在安装前端依赖..."
            npm install
            if ($LASTEXITCODE -ne 0) { throw "npm install 失败" }
        }

        Write-Step "运行 TypeScript 类型检查 (vue-tsc --noEmit)"
        npm run typecheck
        if ($LASTEXITCODE -ne 0) { throw "typecheck 未通过" }

        if ($Fix) {
            Write-Step "运行 ESLint --fix"
            npm run lint:fix
        } else {
            Write-Step "运行 ESLint"
            npm run lint
        }

        if ($LASTEXITCODE -ne 0) { throw "lint 未通过" }

        Write-Host ""
        Write-Host "类型检查与 lint 全部通过。" -ForegroundColor Green
    } finally {
        Pop-Location
    }
} catch {
    Write-Host ""
    Write-Host "检查失败: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
