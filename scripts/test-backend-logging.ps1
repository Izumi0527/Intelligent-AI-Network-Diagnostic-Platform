# PowerShell脚本：测试后端日志修复
# 编码：UTF-8 BOM
# 创建时间：2025-09-25

Write-Host "🚀 测试后端日志修复脚本" -ForegroundColor Green
Write-Host "=================================="

# 设置严格模式
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# 获取项目根目录
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"

Write-Host "📂 项目路径: $ProjectRoot"
Write-Host "📂 后端路径: $BackendPath"

# 停止所有Python进程
Write-Host "🔄 停止现有的Python进程..." -ForegroundColor Yellow
try {
    Get-Process -Name "python" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "✅ Python进程已停止"
} catch {
    Write-Host "ℹ️ 没有运行中的Python进程"
}

# 创建日志目录
$LogsPath = Join-Path $ProjectRoot "logs\backend"
if (-not (Test-Path $LogsPath)) {
    New-Item -ItemType Directory -Path $LogsPath -Force | Out-Null
    Write-Host "📁 创建日志目录: $LogsPath"
}

# 切换到后端目录
Set-Location $BackendPath
Write-Host "📂 切换到后端目录"

# 检查虚拟环境
if (-not (Test-Path ".venv")) {
    Write-Host "❌ 未找到 .venv 虚拟环境" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 找到虚拟环境: .venv"

# 启动后端服务
Write-Host "🔄 启动后端服务..." -ForegroundColor Cyan
Write-Host "观察日志输出是否还有重复..." -ForegroundColor Yellow
Write-Host ""

try {
    # 使用uv运行后端服务
    & uv run python run.py --reload
} catch {
    Write-Host "❌ 启动失败: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🎉 后端服务测试完成！" -ForegroundColor Green