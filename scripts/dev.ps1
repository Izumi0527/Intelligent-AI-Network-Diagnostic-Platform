# AI智能网络故障分析平台 - 开发环境启动脚本
# 生成时间: 2025-09-07 21:29

# 设置错误处理
$ErrorActionPreference = "Stop"

# 输出项目信息
Write-Host "🚀 AI智能网络故障分析平台 - 开发环境启动" -ForegroundColor Green
Write-Host "========================================"

# 检查必要目录
if (!(Test-Path "logs")) {
    Write-Host "❌ logs目录不存在，请先运行 scripts\setup.ps1" -ForegroundColor Red
    exit 1
}

# 设置环境变量
$env:APP_ENV = "development"
$env:LOG_LEVEL = "DEBUG"

# 启动后端服务
Write-Host "📦 启动后端服务..."
Set-Location backend

# 检查虚拟环境
$VenvPath = $null
if (Test-Path ".venv") {
    $VenvPath = ".venv"
} elseif (Test-Path "venv") {
    $VenvPath = "venv"
    Write-Host "⚠️ 检测到旧版venv目录，建议重命名为.venv" -ForegroundColor Yellow
} else {
    Write-Host "❌ 未找到虚拟环境，请先创建虚拟环境" -ForegroundColor Red
    exit 1
}

# 激活虚拟环境
$ActivateScript = Join-Path $VenvPath "Scripts\activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
} else {
    Write-Host "❌ 无法找到虚拟环境激活脚本" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 已激活虚拟环境: $VenvPath" -ForegroundColor Green

# 启动后端（后台运行）
Write-Host "🔄 启动FastAPI服务器..."
$BackendProcess = Start-Process -FilePath "uv" -ArgumentList "run python run.py --reload" -RedirectStandardOutput "..\logs\backend_dev.log" -RedirectStandardError "..\logs\backend_dev.log" -PassThru -WindowStyle Hidden
$BackendPID = $BackendProcess.Id
Write-Host "✅ 后端服务已启动 (PID: $BackendPID)" -ForegroundColor Green

# 启动前端服务
Write-Host "📦 启动前端服务..."
Set-Location ..\frontend

# 检查依赖是否已安装
if (!(Test-Path "node_modules")) {
    Write-Host "📥 安装前端依赖..."
    npm install
}

Write-Host "🔄 启动Vite开发服务器..."
$FrontendProcess = Start-Process -FilePath "npm" -ArgumentList "run dev" -RedirectStandardOutput "..\logs\frontend_dev.log" -RedirectStandardError "..\logs\frontend_dev.log" -PassThru -WindowStyle Hidden
$FrontendPID = $FrontendProcess.Id

Write-Host "✅ 前端服务已启动 (PID: $FrontendPID)" -ForegroundColor Green
Write-Host ""
Write-Host "🎉 服务启动完成！" -ForegroundColor Green
Write-Host "========================================"
Write-Host "🌐 前端地址: http://localhost:5173" -ForegroundColor Cyan
Write-Host "🔧 后端API: http://localhost:8000" -ForegroundColor Cyan  
Write-Host "📚 API文档: http://localhost:8000/api/v1/docs" -ForegroundColor Cyan
Write-Host "📋 日志位置: logs\backend_dev.log, logs\frontend_dev.log" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 按 Ctrl+C 停止所有服务" -ForegroundColor Yellow

# 创建停止函数
function Stop-Services {
    Write-Host ""
    Write-Host "🔄 停止服务..."
    try {
        Stop-Process -Id $BackendPID -Force -ErrorAction SilentlyContinue
        Stop-Process -Id $FrontendPID -Force -ErrorAction SilentlyContinue
        Write-Host "✅ 所有服务已停止" -ForegroundColor Green
    } catch {
        Write-Host "⚠️ 停止服务时出现问题: $($_.Exception.Message)" -ForegroundColor Yellow
    }
}

# 注册清理事件
Register-EngineEvent -SourceIdentifier PowerShell.Exiting -Action { Stop-Services }

try {
    # 等待进程完成或用户中断
    Write-Host "服务运行中... 按任意键停止服务" -ForegroundColor Yellow
    $null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
} finally {
    Stop-Services
    Set-Location ..
}