# PowerShell脚本：启动AI智能网络故障分析平台后端服务
# 编码：UTF-8 BOM
# 创建时间：2025-09-25

param(
    [string]$Port = "8000",
    [string]$HostAddress = "0.0.0.0",
    [switch]$NoReload,
    [switch]$Debug
)

Write-Host "🚀 AI智能网络故障分析平台 - 后端服务启动" -ForegroundColor Green
Write-Host "================================================"

# 设置严格模式和错误处理
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# 获取项目根目录和后端目录
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$LogsPath = Join-Path $ProjectRoot "logs"

Write-Host "📂 项目路径: $ProjectRoot" -ForegroundColor Cyan
Write-Host "📂 后端路径: $BackendPath" -ForegroundColor Cyan

# 检查后端目录是否存在
if (-not (Test-Path $BackendPath)) {
    Write-Host "❌ 后端目录不存在: $BackendPath" -ForegroundColor Red
    exit 1
}

# 创建日志目录结构
$LogDirectories = @("app", "access", "error", "backend", "frontend")
foreach ($LogDir in $LogDirectories) {
    $LogDirPath = Join-Path $LogsPath $LogDir
    if (-not (Test-Path $LogDirPath)) {
        New-Item -ItemType Directory -Path $LogDirPath -Force | Out-Null
        Write-Host "📁 创建日志目录: $LogDir"
    }
}

# 切换到后端目录
Set-Location $BackendPath
Write-Host "📂 切换到后端目录" -ForegroundColor Yellow

# 检查虚拟环境
if (-not (Test-Path ".venv")) {
    Write-Host "❌ 未找到 .venv 虚拟环境" -ForegroundColor Red
    Write-Host "💡 请先运行以下命令创建虚拟环境:" -ForegroundColor Yellow
    Write-Host "   cd backend" -ForegroundColor Gray
    Write-Host "   python -m venv .venv" -ForegroundColor Gray
    Write-Host "   .venv\Scripts\Activate.ps1" -ForegroundColor Gray
    Write-Host "   pip install -r requirements.txt" -ForegroundColor Gray
    exit 1
}

Write-Host "✅ 找到虚拟环境: .venv" -ForegroundColor Green

# 检查.env文件
if (-not (Test-Path ".env")) {
    Write-Host "⚠️ 未找到 .env 配置文件" -ForegroundColor Yellow
    if (Test-Path ".env.example") {
        Write-Host "💡 发现 .env.example 文件，建议复制为 .env 并配置" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ 找到配置文件: .env" -ForegroundColor Green
}

# 设置环境变量
$env:APP_ENV = "development"
if ($Debug) {
    $env:LOG_LEVEL = "DEBUG"
    Write-Host "🐛 启用调试模式 (LOG_LEVEL=DEBUG)" -ForegroundColor Yellow
} else {
    $env:LOG_LEVEL = "INFO"
}

Write-Host "🔧 配置信息:" -ForegroundColor Cyan
Write-Host "   监听地址: $HostAddress" -ForegroundColor Gray
Write-Host "   监听端口: $Port" -ForegroundColor Gray
Write-Host "   热重载: $(-not $NoReload)" -ForegroundColor Gray
Write-Host "   日志级别: $($env:LOG_LEVEL)" -ForegroundColor Gray

# 检查端口是否被占用
try {
    $Connection = Test-NetConnection -ComputerName $HostAddress -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
    if ($Connection) {
        Write-Host "⚠️ 端口 $Port 可能已被占用" -ForegroundColor Yellow
    }
} catch {
    # 忽略端口检查错误
}

# 检查必要的依赖
Write-Host "🔍 检查依赖..." -ForegroundColor Yellow
try {
    & uv --version | Out-Null
    Write-Host "✅ uv 包管理器可用" -ForegroundColor Green
} catch {
    Write-Host "❌ 未找到 uv 包管理器" -ForegroundColor Red
    Write-Host "💡 请先安装 uv: https://github.com/astral-sh/uv" -ForegroundColor Yellow
    exit 1
}

# 启动服务参数
$StartupArgs = @("run", "python", "run.py")
$StartupArgs += "--host", $HostAddress
$StartupArgs += "--port", $Port

if (-not $NoReload) {
    $StartupArgs += "--reload"
}

Write-Host ""
Write-Host "🚀 启动后端服务..." -ForegroundColor Green
Write-Host "================================================"

# 显示访问信息
Write-Host "🌐 服务地址: http://${HostAddress}:${Port}" -ForegroundColor Cyan
Write-Host "📚 API文档: http://${HostAddress}:${Port}/api/v1/docs" -ForegroundColor Cyan
Write-Host "📊 ReDoc文档: http://${HostAddress}:${Port}/api/v1/redoc" -ForegroundColor Cyan
Write-Host ""
Write-Host "💡 按 Ctrl+C 停止服务" -ForegroundColor Yellow
Write-Host "================================================"

# 启动服务
try {
    & uv @StartupArgs
} catch {
    Write-Host ""
    Write-Host "❌ 服务启动失败: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host ""
    Write-Host "🔧 故障排查建议:" -ForegroundColor Yellow
    Write-Host "   1. 检查虚拟环境是否正确创建" -ForegroundColor Gray
    Write-Host "   2. 检查依赖是否已安装" -ForegroundColor Gray
    Write-Host "   3. 检查 .env 配置文件" -ForegroundColor Gray
    Write-Host "   4. 检查端口是否被占用" -ForegroundColor Gray
    exit 1
}

Write-Host ""
Write-Host "🎉 后端服务已停止" -ForegroundColor Green