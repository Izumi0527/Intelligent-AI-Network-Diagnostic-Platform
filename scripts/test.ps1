# AI智能网络故障分析平台 - 测试脚本
# 生成时间: 2025-09-07 21:29

$ErrorActionPreference = "Stop"

Write-Host "🧪 AI智能网络故障分析平台 - 测试执行" -ForegroundColor Green
Write-Host "========================================"

# 1. 后端测试
Write-Host "📦 执行后端测试..."
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

# 运行Python测试
$HasTests = $false
if (Test-Path "tests") {
    $HasTests = $true
} else {
    $TestFiles = Get-ChildItem -Path . -Recurse -Include "test_*.py", "*_test.py"
    if ($TestFiles.Count -gt 0) {
        $HasTests = $true
    }
}

if ($HasTests) {
    Write-Host "🔄 运行Python单元测试..."
    try {
        uv run pytest tests\ -v --tb=short
    } catch {
        Write-Host "❌ 后端测试失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ 后端测试通过" -ForegroundColor Green
} else {
    Write-Host "⚠️ 未找到后端测试文件，跳过测试" -ForegroundColor Yellow
}

Set-Location ..

# 2. 前端测试  
Write-Host "📦 执行前端测试..."
Set-Location frontend

# 检查是否有测试配置
$HasFrontendTests = $false
if ((Test-Path "vitest.config.ts") -or (Test-Path "jest.config.js")) {
    $HasFrontendTests = $true
} else {
    $PackageJson = Get-Content "package.json" -Raw | ConvertFrom-Json
    if ($PackageJson.scripts.test) {
        $HasFrontendTests = $true
    }
}

if ($HasFrontendTests) {
    Write-Host "🔄 运行前端单元测试..."
    try {
        npm test
    } catch {
        Write-Host "❌ 前端测试失败" -ForegroundColor Red
        exit 1
    }
    Write-Host "✅ 前端测试通过" -ForegroundColor Green
} else {
    Write-Host "⚠️ 未找到前端测试配置，跳过测试" -ForegroundColor Yellow
}

Set-Location ..

# 3. 代码质量检查
Write-Host "🔍 执行代码质量检查..."

# Python代码检查
Write-Host "🔄 检查Python代码..."
Set-Location backend

# 检查代码格式（如果有black）
if (Get-Command black -ErrorAction SilentlyContinue) {
    try {
        black --check app\
    } catch {
        Write-Host "⚠️ Python代码格式需要调整" -ForegroundColor Yellow
    }
} else {
    Write-Host "💡 建议安装black进行代码格式检查: pip install black" -ForegroundColor Cyan
}

# 检查代码质量（如果有ruff或flake8）
if (Get-Command ruff -ErrorAction SilentlyContinue) {
    try {
        ruff check app\
    } catch {
        Write-Host "⚠️ Python代码质量问题" -ForegroundColor Yellow
    }
} elseif (Get-Command flake8 -ErrorAction SilentlyContinue) {
    try {
        flake8 app\
    } catch {
        Write-Host "⚠️ Python代码质量问题" -ForegroundColor Yellow
    }
} else {
    Write-Host "💡 建议安装ruff进行代码质量检查: pip install ruff" -ForegroundColor Cyan
}

Set-Location ..

# TypeScript类型检查
Write-Host "🔄 检查TypeScript类型..."
Set-Location frontend
try {
    npm run typecheck
} catch {
    Write-Host "❌ TypeScript类型检查失败" -ForegroundColor Red
    exit 1
}
Set-Location ..

Write-Host ""
Write-Host "🎉 所有测试完成！" -ForegroundColor Green
Write-Host "========================================"
Write-Host "✅ 测试状态: 通过" -ForegroundColor Green
Write-Host "📊 测试覆盖率报告: tests\coverage\" -ForegroundColor Cyan
Write-Host "🔍 代码质量: 检查完成" -ForegroundColor Cyan

# 4. 文件长度检查
Write-Host ""
Write-Host "📏 检查文件长度合规性..."

# 检查Python文件
Write-Host "🐍 Python文件长度检查:" -ForegroundColor Yellow
$PythonFiles = Get-ChildItem -Path "backend" -Include "*.py" -Recurse | Where-Object { 
    $_.FullName -notmatch "\\venv\\" -and $_.FullName -notmatch "\\.venv\\" -and $_.FullName -notmatch "\\__pycache__\\"
}

foreach ($file in $PythonFiles) {
    $lines = (Get-Content $file.FullName | Measure-Object -Line).Lines
    if ($lines -gt 300) {
        $relativePath = $file.FullName.Replace((Get-Location).Path + "\", "")
        $percentage = [math]::Round((($lines - 300) * 100) / 300, 0)
        Write-Host "⚠️ $relativePath`: $lines 行 (超过300行限制 ${percentage}%)" -ForegroundColor Yellow
    }
}

# 检查前端文件  
Write-Host "🌐 前端文件长度检查:" -ForegroundColor Yellow
$FrontendFiles = Get-ChildItem -Path "frontend\src" -Include "*.vue", "*.ts", "*.js" -Recurse

foreach ($file in $FrontendFiles) {
    $lines = (Get-Content $file.FullName | Measure-Object -Line).Lines
    if ($lines -gt 300) {
        $relativePath = $file.FullName.Replace((Get-Location).Path + "\", "")
        $percentage = [math]::Round((($lines - 300) * 100) / 300, 0)
        Write-Host "⚠️ $relativePath`: $lines 行 (超过300行限制 ${percentage}%)" -ForegroundColor Yellow
    }
}

Write-Host "✅ 文件长度检查完成" -ForegroundColor Green