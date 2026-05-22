# AI智能网络故障分析平台 - 前端生产构建脚本
[CmdletBinding()]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$FrontendPath = Join-Path $ProjectRoot "frontend"
$DistPath = Join-Path $FrontendPath "dist"

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

function Format-Size {
    param([long]$Bytes)
    if ($Bytes -ge 1MB) { return "{0:N2} MB" -f ($Bytes / 1MB) }
    if ($Bytes -ge 1KB) { return "{0:N2} KB" -f ($Bytes / 1KB) }
    return "$Bytes B"
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

        Write-Step "运行生产构建 (vue-tsc + vite build)"
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "build 未通过" }

        if (Test-Path -LiteralPath $DistPath) {
            $totalSize = (Get-ChildItem -LiteralPath $DistPath -Recurse -File | Measure-Object -Property Length -Sum).Sum
            Write-Host ""
            Write-Host "构建产物体积统计:" -ForegroundColor Green
            Write-Host ("  dist 目录: {0}" -f (Format-Size $totalSize))

            $assetsPath = Join-Path $DistPath "assets"
            if (Test-Path -LiteralPath $assetsPath) {
                Get-ChildItem -LiteralPath $assetsPath -File | ForEach-Object {
                    Write-Host ("  - {0}: {1}" -f $_.Name, (Format-Size $_.Length))
                }
            }
        }

        Write-Host ""
        Write-Host "前端生产构建完成。" -ForegroundColor Green
    } finally {
        Pop-Location
    }
} catch {
    Write-Host ""
    Write-Host "构建失败: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
