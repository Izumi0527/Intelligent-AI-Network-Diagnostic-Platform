# AI智能网络故障分析平台 - 代码质量检查脚本
# 生成时间: 2025-09-07 21:29

$ErrorActionPreference = "Stop"

Write-Host "🔍 AI智能网络故障分析平台 - 代码质量检查" -ForegroundColor Green
Write-Host "========================================"

# 初始化检查结果
$PythonIssues = 0
$FrontendIssues = 0
$FileLengthIssues = 0

# 1. Python代码检查
Write-Host "🐍 检查Python代码质量..."
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

# 代码格式检查
Write-Host "📝 检查代码格式..."
try {
    uv run black --check app\
    Write-Host "✅ 代码格式检查通过" -ForegroundColor Green
} catch {
    Write-Host "⚠️ 代码格式需要修复，运行: uv run black app\" -ForegroundColor Yellow
    $PythonIssues++
}

# 代码质量检查
Write-Host "🔎 检查代码质量..."
try {
    uv run ruff check app\
    Write-Host "✅ 代码质量检查通过" -ForegroundColor Green
} catch {
    Write-Host "⚠️ 发现代码质量问题，运行 uv run ruff check app\ --fix 自动修复" -ForegroundColor Yellow
    $PythonIssues++
}

# 类型检查
Write-Host "🏷️ 检查类型注解..."
try {
    uv run mypy app\
    Write-Host "✅ 类型检查通过" -ForegroundColor Green
} catch {
    Write-Host "⚠️ 发现类型检查问题" -ForegroundColor Yellow
    $PythonIssues++
}

Set-Location ..

# 2. 前端代码检查
Write-Host ""
Write-Host "🌐 检查前端代码质量..."
Set-Location frontend

# TypeScript类型检查
Write-Host "🏷️ 检查TypeScript类型..."
try {
    npm run typecheck
} catch {
    Write-Host "❌ TypeScript类型检查失败" -ForegroundColor Red
    $FrontendIssues++
}

# ESLint检查（如果配置了）
Write-Host "📋 检查代码规范..."
$HasESLintConfig = (Test-Path ".eslintrc.js") -or (Test-Path ".eslintrc.json") -or (Test-Path "eslint.config.js")

if ($HasESLintConfig) {
    $HasESLint = $false
    try {
        Get-Command eslint -ErrorAction Stop | Out-Null
        $HasESLint = $true
    } catch {
        try {
            npm list eslint 2>$null | Out-Null
            $HasESLint = $true
        } catch {}
    }
    
    if ($HasESLint) {
        try {
            npm run lint 2>$null
        } catch {
            Write-Host "⚠️ ESLint检查发现问题" -ForegroundColor Yellow
            $FrontendIssues++
        }
    }
} else {
    Write-Host "💡 建议配置ESLint进行代码规范检查" -ForegroundColor Cyan
}

Set-Location ..

# 3. 文件长度检查（重点检查）
Write-Host ""
Write-Host "📏 检查文件长度合规性..."
Write-Host "规则：Python文件≤300行，TypeScript/Vue文件≤300行"

# Python文件长度检查
Write-Host ""
Write-Host "🐍 Python文件长度检查：" -ForegroundColor Yellow

$PythonFiles = Get-ChildItem -Path "backend" -Include "*.py" -Recurse | Where-Object { 
    $_.FullName -notmatch "\\venv\\" -and 
    $_.FullName -notmatch "\\.venv\\" -and 
    $_.FullName -notmatch "\\__pycache__\\"
}

foreach ($file in $PythonFiles) {
    $lines = (Get-Content $file.FullName | Measure-Object -Line).Lines
    $relativePath = $file.FullName.Replace((Get-Location).Path + "\", "")
    
    if ($lines -gt 300) {
        $percentage = [math]::Round((($lines - 300) * 100) / 300, 0)
        Write-Host "❌ $relativePath`: $lines 行 (超过300行限制 ${percentage}%)" -ForegroundColor Red
        $FileLengthIssues++
    } elseif ($lines -gt 250) {
        Write-Host "⚠️ $relativePath`: $lines 行 (接近300行限制)" -ForegroundColor Yellow
    }
}

# 前端文件长度检查
Write-Host ""
Write-Host "🌐 前端文件长度检查：" -ForegroundColor Yellow

$FrontendFiles = Get-ChildItem -Path "frontend\src" -Include "*.vue", "*.ts", "*.js" -Recurse

foreach ($file in $FrontendFiles) {
    $lines = (Get-Content $file.FullName | Measure-Object -Line).Lines
    $relativePath = $file.FullName.Replace((Get-Location).Path + "\", "")
    
    if ($lines -gt 300) {
        $percentage = [math]::Round((($lines - 300) * 100) / 300, 0)
        Write-Host "❌ $relativePath`: $lines 行 (超过300行限制 ${percentage}%)" -ForegroundColor Red
        $FileLengthIssues++
    } elseif ($lines -gt 250) {
        Write-Host "⚠️ $relativePath`: $lines 行 (接近300行限制)" -ForegroundColor Yellow
    }
}

# 4. 目录结构检查
Write-Host ""
Write-Host "📁 检查目录结构..."

# 检查必要目录
$RequiredDirs = @("scripts", "logs", "docs", "backend\app", "frontend\src")
foreach ($dir in $RequiredDirs) {
    if (Test-Path $dir) {
        Write-Host "✅ $dir" -ForegroundColor Green
    } else {
        Write-Host "❌ 缺少必要目录: $dir" -ForegroundColor Red
    }
}

# 检查每层文件数量
Write-Host ""
Write-Host "📊 检查目录文件数量（每层建议≤8个）：" -ForegroundColor Yellow

$Directories = Get-ChildItem -Directory -Recurse | Where-Object { 
    $_.FullName -notmatch "\\.git\\" -and 
    $_.FullName -notmatch "\\venv\\" -and 
    $_.FullName -notmatch "\\.venv\\" -and 
    $_.FullName -notmatch "\\node_modules\\"
}

foreach ($dir in $Directories) {
    $fileCount = (Get-ChildItem -Path $dir.FullName -File).Count
    if ($fileCount -gt 8) {
        $relativePath = $dir.FullName.Replace((Get-Location).Path + "\", "")
        Write-Host "⚠️ $relativePath`: $fileCount 个文件 (建议≤8个)" -ForegroundColor Yellow
    }
}

# 5. 总结报告
Write-Host ""
Write-Host "📊 检查结果汇总" -ForegroundColor Green
Write-Host "========================================"

if ($PythonIssues -eq 0) {
    Write-Host "✅ Python代码质量: 优秀" -ForegroundColor Green
} else {
    Write-Host "⚠️ Python代码问题: $PythonIssues 个" -ForegroundColor Yellow
}

if ($FrontendIssues -eq 0) {
    Write-Host "✅ 前端代码质量: 优秀" -ForegroundColor Green
} else {
    Write-Host "⚠️ 前端代码问题: $FrontendIssues 个" -ForegroundColor Yellow
}

# 文件长度问题需要特别统计
$LongPythonFiles = ($PythonFiles | Where-Object { (Get-Content $_.FullName | Measure-Object -Line).Lines -gt 300 }).Count
$LongFrontendFiles = ($FrontendFiles | Where-Object { (Get-Content $_.FullName | Measure-Object -Line).Lines -gt 300 }).Count
$TotalLongFiles = $LongPythonFiles + $LongFrontendFiles

if ($TotalLongFiles -eq 0) {
    Write-Host "✅ 文件长度: 全部合规" -ForegroundColor Green
} else {
    Write-Host "❌ 超长文件: $TotalLongFiles 个需要重构" -ForegroundColor Red
}

Write-Host ""
$TotalIssues = $PythonIssues + $FrontendIssues + $TotalLongFiles

if ($TotalIssues -eq 0) {
    Write-Host "🎉 代码质量检查全部通过！" -ForegroundColor Green
    exit 0
} else {
    Write-Host "⚠️ 发现 $TotalIssues 个问题需要处理" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "💡 改进建议：" -ForegroundColor Cyan
    if ($TotalLongFiles -gt 0) {
        Write-Host "   1. 拆分超长文件（优先级最高）"
    }
    if ($PythonIssues -gt 0) {
        Write-Host "   2. 修复Python代码问题"
    }
    if ($FrontendIssues -gt 0) {
        Write-Host "   3. 修复前端代码问题"
    }
    exit 1
}