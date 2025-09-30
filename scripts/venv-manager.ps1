# PowerShell脚本：虚拟环境管理工具
# 编码：UTF-8 BOM
# 创建时间：2025-09-25

param(
    [Parameter(Position=0)]
    [ValidateSet("create", "activate", "deactivate", "install", "update", "clean", "info")]
    [string]$Action = "info",

    [string]$PythonVersion = "3.9",
    [switch]$Force
)

Write-Host "🐍 Python虚拟环境管理工具" -ForegroundColor Green
Write-Host "================================"

# 设置严格模式
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# 获取项目路径
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$BackendPath = Join-Path $ProjectRoot "backend"
$VenvPath = Join-Path $BackendPath ".venv"
$RequirementsPath = Join-Path $BackendPath "requirements.txt"

Write-Host "📂 项目路径: $ProjectRoot" -ForegroundColor Cyan
Write-Host "📂 后端路径: $BackendPath" -ForegroundColor Cyan
Write-Host "🐍 虚拟环境路径: $VenvPath" -ForegroundColor Cyan

# 检查后端目录
if (-not (Test-Path $BackendPath)) {
    Write-Host "❌ 后端目录不存在: $BackendPath" -ForegroundColor Red
    exit 1
}

# 切换到后端目录
Set-Location $BackendPath

function Test-VenvExists {
    return (Test-Path $VenvPath) -and (Test-Path (Join-Path $VenvPath "Scripts\python.exe"))
}

function Test-VenvActive {
    return $env:VIRTUAL_ENV -eq $VenvPath
}

function Show-VenvInfo {
    Write-Host ""
    Write-Host "📊 虚拟环境状态:" -ForegroundColor Yellow

    if (Test-VenvExists) {
        Write-Host "   状态: ✅ 已创建" -ForegroundColor Green

        if (Test-VenvActive) {
            Write-Host "   激活: ✅ 已激活" -ForegroundColor Green
        } else {
            Write-Host "   激活: ❌ 未激活" -ForegroundColor Yellow
        }

        # 显示Python版本
        try {
            $PythonExe = Join-Path $VenvPath "Scripts\python.exe"
            $PythonVersionOutput = & $PythonExe --version 2>&1
            Write-Host "   Python版本: $PythonVersionOutput" -ForegroundColor Cyan
        } catch {
            Write-Host "   Python版本: 无法获取" -ForegroundColor Red
        }

        # 显示已安装包数量
        try {
            $PipExe = Join-Path $VenvPath "Scripts\pip.exe"
            $PackageCount = (& $PipExe list --format=json | ConvertFrom-Json).Count
            Write-Host "   已安装包: $PackageCount 个" -ForegroundColor Cyan
        } catch {
            Write-Host "   已安装包: 无法获取" -ForegroundColor Red
        }

    } else {
        Write-Host "   状态: ❌ 未创建" -ForegroundColor Red
    }

    Write-Host "   路径: $VenvPath" -ForegroundColor Gray
    Write-Host ""
}

# 执行操作
switch ($Action) {
    "create" {
        Write-Host "🔨 创建虚拟环境..." -ForegroundColor Yellow

        if ((Test-VenvExists) -and (-not $Force)) {
            Write-Host "⚠️ 虚拟环境已存在，使用 -Force 参数强制重建" -ForegroundColor Yellow
            Show-VenvInfo
            exit 0
        }

        if ($Force -and (Test-VenvExists)) {
            Write-Host "🗑️ 删除现有虚拟环境..." -ForegroundColor Yellow
            Remove-Item $VenvPath -Recurse -Force
        }

        try {
            # 检查Python是否可用
            $PythonCommand = "python"
            try {
                & python --version | Out-Null
            } catch {
                Write-Host "❌ 未找到Python解释器" -ForegroundColor Red
                Write-Host "💡 请确保Python已安装并添加到PATH" -ForegroundColor Yellow
                exit 1
            }

            Write-Host "✅ 找到Python解释器" -ForegroundColor Green

            # 创建虚拟环境
            & python -m venv $VenvPath
            Write-Host "✅ 虚拟环境创建成功" -ForegroundColor Green

            # 升级pip
            $PipExe = Join-Path $VenvPath "Scripts\pip.exe"
            Write-Host "🔄 升级pip..." -ForegroundColor Yellow
            & $PipExe install --upgrade pip

            Write-Host "🎉 虚拟环境创建完成！" -ForegroundColor Green
            Write-Host "💡 使用 'activate' 命令激活虚拟环境" -ForegroundColor Yellow

        } catch {
            Write-Host "❌ 创建虚拟环境失败: $($_.Exception.Message)" -ForegroundColor Red
            exit 1
        }
    }

    "activate" {
        if (-not (Test-VenvExists)) {
            Write-Host "❌ 虚拟环境不存在，请先创建" -ForegroundColor Red
            Write-Host "💡 使用命令: .\scripts\venv-manager.ps1 create" -ForegroundColor Yellow
            exit 1
        }

        $ActivateScript = Join-Path $VenvPath "Scripts\Activate.ps1"

        Write-Host "🔄 激活虚拟环境..." -ForegroundColor Yellow
        Write-Host "💡 请在新的PowerShell窗口中运行以下命令:" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "   $ActivateScript" -ForegroundColor Green
        Write-Host ""
        Write-Host "或者直接运行:" -ForegroundColor Cyan
        Write-Host "   .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
    }

    "deactivate" {
        if (Test-VenvActive) {
            Write-Host "🔄 停用虚拟环境..." -ForegroundColor Yellow
            Write-Host "💡 在激活的终端中运行: deactivate" -ForegroundColor Cyan
        } else {
            Write-Host "ℹ️ 虚拟环境未激活" -ForegroundColor Gray
        }
    }

    "install" {
        if (-not (Test-VenvExists)) {
            Write-Host "❌ 虚拟环境不存在，请先创建" -ForegroundColor Red
            exit 1
        }

        $PipExe = Join-Path $VenvPath "Scripts\pip.exe"

        Write-Host "📦 安装项目依赖..." -ForegroundColor Yellow

        if (Test-Path $RequirementsPath) {
            Write-Host "✅ 找到 requirements.txt" -ForegroundColor Green
            try {
                & $PipExe install -r $RequirementsPath
                Write-Host "🎉 依赖安装完成！" -ForegroundColor Green
            } catch {
                Write-Host "❌ 依赖安装失败: $($_.Exception.Message)" -ForegroundColor Red
                exit 1
            }
        } else {
            Write-Host "⚠️ 未找到 requirements.txt 文件" -ForegroundColor Yellow
            Write-Host "💡 手动安装核心依赖..." -ForegroundColor Cyan

            $CorePackages = @(
                "fastapi", "uvicorn", "pydantic", "pydantic-settings",
                "sse-starlette", "netmiko", "aiohttp", "python-dotenv",
                "httpx", "paramiko", "python-jose", "passlib", "bcrypt", "requests"
            )

            foreach ($Package in $CorePackages) {
                Write-Host "📦 安装 $Package..." -ForegroundColor Gray
                & $PipExe install $Package
            }

            Write-Host "🎉 核心依赖安装完成！" -ForegroundColor Green
        }
    }

    "update" {
        if (-not (Test-VenvExists)) {
            Write-Host "❌ 虚拟环境不存在，请先创建" -ForegroundColor Red
            exit 1
        }

        $PipExe = Join-Path $VenvPath "Scripts\pip.exe"

        Write-Host "🔄 更新已安装的包..." -ForegroundColor Yellow
        try {
            # 升级pip
            & $PipExe install --upgrade pip

            # 更新所有包
            $InstalledPackages = & $PipExe list --outdated --format=json | ConvertFrom-Json

            if ($InstalledPackages.Count -gt 0) {
                Write-Host "📦 发现 $($InstalledPackages.Count) 个可更新的包" -ForegroundColor Cyan

                foreach ($Package in $InstalledPackages) {
                    Write-Host "📦 更新 $($Package.name)..." -ForegroundColor Gray
                    & $PipExe install --upgrade $Package.name
                }

                Write-Host "🎉 包更新完成！" -ForegroundColor Green
            } else {
                Write-Host "✅ 所有包都是最新版本" -ForegroundColor Green
            }

        } catch {
            Write-Host "❌ 更新失败: $($_.Exception.Message)" -ForegroundColor Red
            exit 1
        }
    }

    "clean" {
        if (Test-VenvExists) {
            if ($Force) {
                Write-Host "🗑️ 删除虚拟环境..." -ForegroundColor Yellow
                Remove-Item $VenvPath -Recurse -Force
                Write-Host "✅ 虚拟环境已删除" -ForegroundColor Green
            } else {
                Write-Host "⚠️ 即将删除虚拟环境，使用 -Force 参数确认" -ForegroundColor Yellow
                Show-VenvInfo
            }
        } else {
            Write-Host "ℹ️ 虚拟环境不存在" -ForegroundColor Gray
        }
    }

    "info" {
        Show-VenvInfo

        Write-Host "💡 可用命令:" -ForegroundColor Yellow
        Write-Host "   create   - 创建虚拟环境" -ForegroundColor Gray
        Write-Host "   activate - 显示激活命令" -ForegroundColor Gray
        Write-Host "   install  - 安装项目依赖" -ForegroundColor Gray
        Write-Host "   update   - 更新已安装包" -ForegroundColor Gray
        Write-Host "   clean    - 删除虚拟环境" -ForegroundColor Gray
        Write-Host "   info     - 显示状态信息" -ForegroundColor Gray
        Write-Host ""
        Write-Host "💡 使用示例:" -ForegroundColor Cyan
        Write-Host "   .\scripts\venv-manager.ps1 create" -ForegroundColor Green
        Write-Host "   .\scripts\venv-manager.ps1 install" -ForegroundColor Green
    }
}

Write-Host ""