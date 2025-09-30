# AI智能网络故障分析平台 - 构建脚本
# 生成时间: 2025-09-07 21:29

$ErrorActionPreference = "Stop"

Write-Host "🔨 AI智能网络故障分析平台 - 生产构建" -ForegroundColor Green
Write-Host "========================================"

# 设置构建环境
$env:NODE_ENV = "production"
$env:APP_ENV = "production"

# 1. 清理之前的构建
Write-Host "🧹 清理构建目录..."
if (Test-Path "frontend\dist") {
    Remove-Item -Path "frontend\dist" -Recurse -Force
}
if (Test-Path "backend\dist") {
    Remove-Item -Path "backend\dist" -Recurse -Force
}
if (!(Test-Path "dist")) {
    New-Item -ItemType Directory -Path "dist" -Force | Out-Null
}
Write-Host "✅ 构建目录已清理" -ForegroundColor Green

# 2. 构建前端
Write-Host "📦 构建前端应用..."
Set-Location frontend

# 检查依赖
if (!(Test-Path "node_modules")) {
    Write-Host "📥 安装前端依赖..."
    npm ci  # 生产环境使用ci而不是install
}

# 类型检查
Write-Host "🔍 执行TypeScript类型检查..."
try {
    npm run typecheck
} catch {
    Write-Host "❌ TypeScript类型检查失败" -ForegroundColor Red
    exit 1
}

# 构建
Write-Host "🔄 构建前端..."
try {
    npm run build
} catch {
    Write-Host "❌ 前端构建失败" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 前端构建完成" -ForegroundColor Green
Set-Location ..

# 3. 检查后端依赖
Write-Host "📦 检查后端依赖..."
Set-Location backend

# 激活虚拟环境
$VenvPath = $null
if (Test-Path ".venv") {
    $VenvPath = ".venv"
} elseif (Test-Path "venv") {
    $VenvPath = "venv"
} else {
    Write-Host "❌ 未找到虚拟环境" -ForegroundColor Red
    exit 1
}

$ActivateScript = Join-Path $VenvPath "Scripts\activate.ps1"
if (Test-Path $ActivateScript) {
    & $ActivateScript
} else {
    Write-Host "❌ 无法找到虚拟环境激活脚本" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 已激活虚拟环境" -ForegroundColor Green

# 4. 运行测试（如果存在）
Write-Host "🧪 运行测试套件..."
if ((Test-Path "pytest.ini") -or (Test-Path "pyproject.toml")) {
    try {
        uv run pytest tests\ -v
    } catch {
        Write-Host "❌ 测试失败，构建终止" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ 所有测试通过" -ForegroundColor Green
} else {
    Write-Host "⚠️ 未找到测试配置，跳过测试" -ForegroundColor Yellow
}

Set-Location ..

# 5. 创建部署包
Write-Host "📦 创建部署包..."
$BuildTime = Get-Date -Format "yyyyMMdd_HHmmss"
$PackageName = "ai-network-platform_$BuildTime.zip"

# PowerShell压缩，排除不需要的文件
$ExcludePatterns = @(
    "backend\.venv\*",
    "backend\venv\*",
    "backend\__pycache__\*",
    "backend\**\__pycache__\*",
    "frontend\node_modules\*",
    "frontend\.vite\*",
    ".git\*",
    "logs\*",
    "discuss\*"
)

try {
    # 使用.NET压缩，更好地控制排除文件
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $ArchivePath = Join-Path (Get-Location) "dist\$PackageName"
    
    # 创建临时目录用于构建
    $TempDir = Join-Path $env:TEMP "ai-platform-build"
    if (Test-Path $TempDir) {
        Remove-Item -Path $TempDir -Recurse -Force
    }
    New-Item -ItemType Directory -Path $TempDir -Force | Out-Null
    
    # 复制必要文件，排除不需要的内容
    $ItemsToInclude = @("backend\app", "backend\run.py", "backend\requirements.txt", "backend\.env", "frontend\dist", "scripts\*.ps1")
    foreach ($item in $ItemsToInclude) {
        if (Test-Path $item) {
            $DestPath = Join-Path $TempDir (Split-Path $item -Leaf)
            Copy-Item -Path $item -Destination $DestPath -Recurse -Force
        }
    }
    
    # 创建压缩包
    [System.IO.Compression.ZipFile]::CreateFromDirectory($TempDir, $ArchivePath)
    
    # 清理临时目录
    Remove-Item -Path $TempDir -Recurse -Force
    
} catch {
    Write-Host "❌ 创建部署包失败: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 部署包创建完成: dist\$PackageName" -ForegroundColor Green

# 6. 显示构建信息
Write-Host ""
Write-Host "🎉 构建完成！" -ForegroundColor Green
Write-Host "========================================"
Write-Host "📦 前端构建: frontend\dist\"
Write-Host "📦 部署包: dist\$PackageName"
Write-Host "📊 构建信息:"

if (Test-Path "frontend\dist") {
    $DistSize = (Get-ChildItem -Path "frontend\dist" -Recurse | Measure-Object -Property Length -Sum).Sum
    $DistSizeMB = [math]::Round($DistSize / 1MB, 2)
    Write-Host "   前端包大小: $DistSizeMB MB"
}

if (Test-Path "dist\$PackageName") {
    $PackageSize = (Get-Item "dist\$PackageName").Length
    $PackageSizeMB = [math]::Round($PackageSize / 1MB, 2)
    Write-Host "   部署包大小: $PackageSizeMB MB"
}

Write-Host "   构建时间: $(Get-Date)"

Write-Host ""
Write-Host "⚡ 部署说明:" -ForegroundColor Cyan
Write-Host "   1. 上传部署包到服务器"
Write-Host "   2. 解压并安装依赖"
Write-Host "   3. 配置环境变量"
Write-Host "   4. 运行 scripts\prod.ps1 启动服务"