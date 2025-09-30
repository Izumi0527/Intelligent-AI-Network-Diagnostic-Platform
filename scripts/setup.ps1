# AI智能网络故障分析平台 - 环境初始化脚本
# 生成时间: 2025-09-07 21:29

$ErrorActionPreference = "Stop"

Write-Host "🔧 AI智能网络故障分析平台 - 环境初始化" -ForegroundColor Green
Write-Host "========================================"

# 1. 创建必要的目录结构
Write-Host "📁 创建目录结构..."

# 创建日志目录
$LogDirs = @("logs\app", "logs\access", "logs\error", "logs\backend", "logs\frontend")
foreach ($dir in $LogDirs) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

# 创建后端模块目录（为后续重构预备）
$BackendDirs = @(
    "backend\app\core\network\telnet",
    "backend\app\core\network\ssh",
    "backend\app\core\network\telnet\devices",
    "backend\app\services\ai\models",
    "backend\app\services\ai\deepseek"
)
foreach ($dir in $BackendDirs) {
    if (!(Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}

Write-Host "✅ 目录结构创建完成" -ForegroundColor Green

# 2. 检查并重命名虚拟环境，安装uv工具
Write-Host "🔄 检查虚拟环境和uv工具..."
Set-Location backend

if ((Test-Path "venv") -and !(Test-Path ".venv")) {
    Write-Host "📦 重命名 venv → .venv"
    Rename-Item -Path "venv" -NewName ".venv"
    Write-Host "✅ 虚拟环境已重命名" -ForegroundColor Green
} elseif (Test-Path ".venv") {
    Write-Host "✅ .venv 环境已存在" -ForegroundColor Green
} else {
    Write-Host "⚠️ 未找到虚拟环境，正在创建..." -ForegroundColor Yellow
    python -m venv .venv
    Write-Host "✅ 虚拟环境已创建" -ForegroundColor Green
}

# 激活虚拟环境并安装uv
if (Test-Path ".venv\Scripts\activate.ps1") {
    & .venv\Scripts\activate.ps1
    
    # 安装uv工具
    Write-Host "⚡ 安装uv工具..."
    if (!(Get-Command uv -ErrorAction SilentlyContinue)) {
        Write-Host "正在安装uv..."
        python -m pip install uv
        Write-Host "✅ uv工具安装完成" -ForegroundColor Green
    } else {
        Write-Host "✅ uv工具已安装" -ForegroundColor Green
    }
    
    # 安装项目依赖
    Write-Host "📦 使用uv安装Python依赖..."
    if (Test-Path "pyproject.toml") {
        uv sync --dev  # 安装项目依赖和开发依赖
        Write-Host "✅ 已使用uv安装所有依赖" -ForegroundColor Green
    } elseif (Test-Path "requirements.txt") {
        Write-Host "⚠️ 发现旧的requirements.txt，建议迁移到pyproject.toml" -ForegroundColor Yellow
        uv pip install -r requirements.txt
        Write-Host "✅ 已安装requirements.txt中的依赖" -ForegroundColor Green
    } else {
        Write-Host "❌ 未找到pyproject.toml或requirements.txt文件" -ForegroundColor Red
    }
} else {
    Write-Host "❌ 无法激活虚拟环境" -ForegroundColor Red
}

Set-Location ..

# 3. 检查前端依赖
Write-Host "📦 检查前端依赖..."
Set-Location frontend

if (!(Test-Path "node_modules")) {
    Write-Host "📥 安装前端依赖..."
    npm install
    Write-Host "✅ 前端依赖安装完成" -ForegroundColor Green
} else {
    Write-Host "✅ 前端依赖已存在" -ForegroundColor Green
}

Set-Location ..

# 4. 创建环境配置文件示例
Write-Host "⚙️ 检查配置文件..."

if (!(Test-Path "backend\.env")) {
    if (Test-Path "backend\.env.example") {
        Write-Host "📝 复制环境配置模板..."
        Copy-Item "backend\.env.example" "backend\.env"
        Write-Host "⚠️ 请编辑 backend\.env 文件配置API密钥等参数" -ForegroundColor Yellow
    } else {
        Write-Host "⚠️ 未找到 .env.example 文件" -ForegroundColor Yellow
    }
} else {
    Write-Host "✅ 环境配置文件已存在" -ForegroundColor Green
}

# 5. 设置脚本执行权限
Write-Host "🔐 设置PowerShell执行策略..."
try {
    $CurrentPolicy = Get-ExecutionPolicy -Scope CurrentUser
    if ($CurrentPolicy -eq "Restricted") {
        Write-Host "设置PowerShell执行策略为RemoteSigned..." -ForegroundColor Yellow
        Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
        Write-Host "✅ PowerShell执行策略已设置" -ForegroundColor Green
    } else {
        Write-Host "✅ PowerShell执行策略已配置: $CurrentPolicy" -ForegroundColor Green
    }
} catch {
    Write-Host "⚠️ 无法自动设置执行策略，请手动运行:" -ForegroundColor Yellow
    Write-Host "   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
}

Write-Host ""
Write-Host "🎉 环境初始化完成！" -ForegroundColor Green
Write-Host "========================================"
Write-Host "📂 目录结构:"
Write-Host "   logs\          - 日志文件目录"
Write-Host "   scripts\       - 运行脚本目录"  
Write-Host "   backend\.venv\ - Python虚拟环境"
Write-Host "   frontend\      - 前端项目"
Write-Host ""
Write-Host "⚡ 下一步:" -ForegroundColor Cyan
Write-Host "   1. 编辑 backend\.env 配置文件"
Write-Host "   2. 运行 scripts\dev.ps1 启动开发环境"
Write-Host "   3. 运行 scripts\test.ps1 执行测试"