# 启动脚本静态验证：确保 scripts 目录只保留统一入口和缓存清理脚本，并具备顺序启动结构。
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ScriptsDir = Join-Path $ProjectRoot "scripts"
$ReadmePath = Join-Path $ProjectRoot "README.md"

function Assert-True {
    param(
        [bool]$Condition,
        [string]$Message
    )

    if (-not $Condition) {
        throw $Message
    }
}

function Assert-Contains {
    param(
        [string]$Content,
        [string]$Pattern,
        [string]$Message
    )

    Assert-True ($Content -match $Pattern) $Message
}

$ExpectedScripts = @(
    "dev.ps1",
    "prod.ps1",
    "dev.sh",
    "prod.sh",
    "clean-python-cache.ps1",
    "clean-python-cache.sh"
)
$ActualScripts = Get-ChildItem -Path $ScriptsDir -File | Select-Object -ExpandProperty Name | Sort-Object

$UnexpectedScripts = @($ActualScripts | Where-Object { $_ -notin $ExpectedScripts })
$MissingScripts = @($ExpectedScripts | Where-Object { $_ -notin $ActualScripts })

Assert-True ($UnexpectedScripts.Count -eq 0) "scripts 目录存在多余脚本: $($UnexpectedScripts -join ', ')"
Assert-True ($MissingScripts.Count -eq 0) "scripts 目录缺少必要脚本: $($MissingScripts -join ', ')"

foreach ($scriptName in @("dev.ps1", "prod.ps1")) {
    $path = Join-Path $ScriptsDir $scriptName
    $content = Get-Content -Path $path -Raw
    Assert-Contains $content "function Start-ManagedWindow" "$scriptName 缺少窗口启动函数"
    Assert-Contains $content "function Wait-BackendReady" "$scriptName 缺少后端健康检查函数"
    Assert-Contains $content "PYTHONDONTWRITEBYTECODE" "$scriptName 启动后端前必须禁用 Python 字节码缓存写入"
    Assert-Contains $content "node_modules[\\/\\\\]\.bin[\\/\\\\]vite\.cmd" "$scriptName 应直接调用本地 vite.cmd，避免 npm run 参数被吞掉"
    Assert-Contains $content "--host" "$scriptName 缺少 Vite host 参数"
    Assert-Contains $content "--port" "$scriptName 缺少 Vite port 参数"
    Assert-True (-not ($content -match "npm run (dev|preview) --")) "$scriptName 不应通过 npm run 透传 Vite 参数"
    Assert-Contains $content "/api/v1/health" "$scriptName 缺少后端健康检查地址"
    Assert-Contains $content "Start-ManagedWindow[\s\S]+backend[\s\S]+Wait-BackendReady[\s\S]+Start-ManagedWindow[\s\S]+frontend" "$scriptName 未体现先后端再前端的启动顺序"
}

foreach ($scriptName in @("dev.sh", "prod.sh")) {
    $path = Join-Path $ScriptsDir $scriptName
    $content = Get-Content -Path $path -Raw
    Assert-Contains $content "start_managed_window" "$scriptName 缺少窗口启动函数"
    Assert-Contains $content "wait_backend_ready" "$scriptName 缺少后端健康检查函数"
    Assert-Contains $content "PYTHONDONTWRITEBYTECODE" "$scriptName 启动后端前必须禁用 Python 字节码缓存写入"
    Assert-Contains $content "node_modules/\.bin/vite" "$scriptName 应直接调用本地 vite，避免 npm run 参数被吞掉"
    Assert-Contains $content "--host" "$scriptName 缺少 Vite host 参数"
    Assert-Contains $content "--port" "$scriptName 缺少 Vite port 参数"
    Assert-True (-not ($content -match "npm run (dev|preview) --")) "$scriptName 不应通过 npm run 透传 Vite 参数"
    Assert-Contains $content "/api/v1/health" "$scriptName 缺少后端健康检查地址"
    Assert-Contains $content "start_managed_window[\s\S]+backend[\s\S]+wait_backend_ready[\s\S]+start_managed_window[\s\S]+frontend" "$scriptName 未体现先后端再前端的启动顺序"
}

$PowerShellCleaner = Get-Content -Path (Join-Path $ScriptsDir "clean-python-cache.ps1") -Raw
Assert-Contains $PowerShellCleaner "__pycache__" "clean-python-cache.ps1 必须清理 __pycache__ 目录"
Assert-Contains $PowerShellCleaner "\.pyc" "clean-python-cache.ps1 必须清理 .pyc 文件"
Assert-Contains $PowerShellCleaner "\.pyo" "clean-python-cache.ps1 必须清理 .pyo 文件"
Assert-Contains $PowerShellCleaner "Remove-Item" "clean-python-cache.ps1 必须执行删除操作"

$ShellCleaner = Get-Content -Path (Join-Path $ScriptsDir "clean-python-cache.sh") -Raw
Assert-Contains $ShellCleaner "__pycache__" "clean-python-cache.sh 必须清理 __pycache__ 目录"
Assert-Contains $ShellCleaner "\.pyc" "clean-python-cache.sh 必须清理 .pyc 文件"
Assert-Contains $ShellCleaner "\.pyo" "clean-python-cache.sh 必须清理 .pyo 文件"
Assert-Contains $ShellCleaner "find" "clean-python-cache.sh 必须使用 find 定位缓存文件"

$Readme = Get-Content -Path $ReadmePath -Raw
$RemovedScriptNames = @(
    "backend_dev.sh",
    "setup.sh",
    "test.sh",
    "build.sh",
    "lint.sh",
    "setup.ps1",
    "test.ps1",
    "build.ps1",
    "lint.ps1",
    "start-backend.ps1",
    "venv-manager.ps1",
    "test-backend-logging.ps1"
)

foreach ($removedName in $RemovedScriptNames) {
    Assert-True (-not $Readme.Contains($removedName)) "README 仍引用已合并脚本: $removedName"
}

Assert-True ($Readme.Contains("clean-python-cache.ps1")) "README 缺少 Windows Python 缓存清理脚本说明"
Assert-True ($Readme.Contains("clean-python-cache.sh")) "README 缺少 Shell Python 缓存清理脚本说明"
Assert-True ($Readme.Contains("PYTHONDONTWRITEBYTECODE=1")) "README 缺少 Python 字节码缓存禁用说明"

Write-Host "启动脚本静态验证通过" -ForegroundColor Green
