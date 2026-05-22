# Static checks for unified launch and maintenance scripts.
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
    "build.ps1",
    "lint.ps1",
    "build.sh",
    "lint.sh",
    "p3_axe_audit.py",
    "clean-python-cache.ps1",
    "clean-python-cache.sh"
)
$ActualScripts = Get-ChildItem -Path $ScriptsDir -File | Select-Object -ExpandProperty Name | Sort-Object

$UnexpectedScripts = @($ActualScripts | Where-Object { $_ -notin $ExpectedScripts })
$MissingScripts = @($ExpectedScripts | Where-Object { $_ -notin $ActualScripts })

Assert-True ($UnexpectedScripts.Count -eq 0) "scripts directory has unexpected files: $($UnexpectedScripts -join ', ')"
Assert-True ($MissingScripts.Count -eq 0) "scripts directory is missing files: $($MissingScripts -join ', ')"

foreach ($scriptName in @("dev.ps1", "prod.ps1")) {
    $path = Join-Path $ScriptsDir $scriptName
    $content = Get-Content -Path $path -Raw
    Assert-Contains $content "function Start-ManagedWindow" "$scriptName missing Start-ManagedWindow"
    Assert-Contains $content "function Wait-BackendReady" "$scriptName missing Wait-BackendReady"
    Assert-Contains $content "PYTHONDONTWRITEBYTECODE" "$scriptName must disable Python bytecode cache"
    Assert-Contains $content "node_modules[\\/\\]\.bin[\\/\\]vite\.cmd" "$scriptName must call local vite.cmd"
    Assert-Contains $content "--host" "$scriptName missing Vite host argument"
    Assert-Contains $content "--port" "$scriptName missing Vite port argument"
    Assert-True (-not ($content -match "npm run (dev|preview) --")) "$scriptName must not forward Vite args through npm run"
    Assert-Contains $content "/api/v1/health" "$scriptName missing backend health check"
    Assert-Contains $content "Start-ManagedWindow[\s\S]+backend[\s\S]+Wait-BackendReady[\s\S]+Start-ManagedWindow[\s\S]+frontend" "$scriptName must start backend before frontend"
}

foreach ($scriptName in @("dev.sh", "prod.sh")) {
    $path = Join-Path $ScriptsDir $scriptName
    $content = Get-Content -Path $path -Raw
    Assert-Contains $content "start_managed_window" "$scriptName missing start_managed_window"
    Assert-Contains $content "wait_backend_ready" "$scriptName missing wait_backend_ready"
    Assert-Contains $content "PYTHONDONTWRITEBYTECODE" "$scriptName must disable Python bytecode cache"
    Assert-Contains $content "node_modules/\.bin/vite" "$scriptName must call local vite"
    Assert-Contains $content "--host" "$scriptName missing Vite host argument"
    Assert-Contains $content "--port" "$scriptName missing Vite port argument"
    Assert-True (-not ($content -match "npm run (dev|preview) --")) "$scriptName must not forward Vite args through npm run"
    Assert-Contains $content "/api/v1/health" "$scriptName missing backend health check"
    Assert-Contains $content "start_managed_window[\s\S]+backend[\s\S]+wait_backend_ready[\s\S]+start_managed_window[\s\S]+frontend" "$scriptName must start backend before frontend"
}

$PowerShellCleaner = Get-Content -Path (Join-Path $ScriptsDir "clean-python-cache.ps1") -Raw
Assert-Contains $PowerShellCleaner "__pycache__" "clean-python-cache.ps1 must clean __pycache__"
Assert-Contains $PowerShellCleaner "\.pyc" "clean-python-cache.ps1 must clean .pyc files"
Assert-Contains $PowerShellCleaner "\.pyo" "clean-python-cache.ps1 must clean .pyo files"
Assert-Contains $PowerShellCleaner "Remove-Item" "clean-python-cache.ps1 must remove files"

$ShellCleaner = Get-Content -Path (Join-Path $ScriptsDir "clean-python-cache.sh") -Raw
Assert-Contains $ShellCleaner "__pycache__" "clean-python-cache.sh must clean __pycache__"
Assert-Contains $ShellCleaner "\.pyc" "clean-python-cache.sh must clean .pyc files"
Assert-Contains $ShellCleaner "\.pyo" "clean-python-cache.sh must clean .pyo files"
Assert-Contains $ShellCleaner "find" "clean-python-cache.sh must use find"

$Readme = Get-Content -Path $ReadmePath -Raw
$RemovedScriptNames = @(
    "backend_dev.sh",
    "setup.sh",
    "test.sh",
    "setup.ps1",
    "test.ps1",
    "start-backend.ps1",
    "venv-manager.ps1",
    "test-backend-logging.ps1"
)

foreach ($removedName in $RemovedScriptNames) {
    Assert-True (-not $Readme.Contains($removedName)) "README still references removed script: $removedName"
}

Assert-True ($Readme.Contains("build.ps1")) "README missing build.ps1"
Assert-True ($Readme.Contains("build.sh")) "README missing build.sh"
Assert-True ($Readme.Contains("lint.ps1")) "README missing lint.ps1"
Assert-True ($Readme.Contains("lint.sh")) "README missing lint.sh"
Assert-True ($Readme.Contains("p3_axe_audit.py")) "README missing p3_axe_audit.py"
Assert-True ($Readme.Contains("clean-python-cache.ps1")) "README missing clean-python-cache.ps1"
Assert-True ($Readme.Contains("clean-python-cache.sh")) "README missing clean-python-cache.sh"
Assert-True ($Readme.Contains("PYTHONDONTWRITEBYTECODE=1")) "README missing PYTHONDONTWRITEBYTECODE=1"

Write-Host "Launch script static verification passed" -ForegroundColor Green
