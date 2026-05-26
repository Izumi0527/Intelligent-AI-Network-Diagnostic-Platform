# Static checks for unified launch and maintenance scripts.
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$ScriptsDir = Join-Path $ProjectRoot "scripts"
$ReadmePath = Join-Path $ProjectRoot "README.md"
$ViteConfigPath = Join-Path $ProjectRoot "frontend/vite.config.ts"
$DefaultFrontendPort = "5180"

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
    "backend-check.ps1",
    "build.sh",
    "lint.sh",
    "backend-check.sh",
    "p3_axe_audit.py",
    "p6_axe_audit.py",
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

$DevPowerShell = Get-Content -Path (Join-Path $ScriptsDir "dev.ps1") -Raw
Assert-True $DevPowerShell.Contains("[int]`$FrontendPort = $DefaultFrontendPort") "dev.ps1 must default frontend port to $DefaultFrontendPort"
Assert-Contains $DevPowerShell "Get-DevelopmentInternalApiToken" "dev.ps1 must prepare development internal API token"
Assert-Contains $DevPowerShell "API_AUTH_ENABLED" "dev.ps1 must enable backend internal API auth"
Assert-Contains $DevPowerShell "INTERNAL_API_TOKEN" "dev.ps1 must pass backend internal API token"
Assert-Contains $DevPowerShell "VITE_INTERNAL_API_TOKEN" "dev.ps1 must pass matching frontend internal API token"

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

$DevShell = Get-Content -Path (Join-Path $ScriptsDir "dev.sh") -Raw
$ExpectedDevShellPort = 'FRONTEND_PORT="${FRONTEND_PORT:-' + $DefaultFrontendPort + '}"'
Assert-True $DevShell.Contains($ExpectedDevShellPort) "dev.sh must default frontend port to $DefaultFrontendPort"
Assert-Contains $DevShell "development_internal_api_token" "dev.sh must prepare development internal API token"
Assert-Contains $DevShell "API_AUTH_ENABLED" "dev.sh must enable backend internal API auth"
Assert-Contains $DevShell "INTERNAL_API_TOKEN" "dev.sh must pass backend internal API token"
Assert-Contains $DevShell "VITE_INTERNAL_API_TOKEN" "dev.sh must pass matching frontend internal API token"

$ViteConfig = Get-Content -Path $ViteConfigPath -Raw
Assert-Contains $ViteConfig "DEFAULT_DEV_HOST\s*=\s*'127\.0\.0\.1'" "vite.config.ts must default to loopback host for local development"
Assert-Contains $ViteConfig "DEFAULT_DEV_PORT\s*=\s*$DefaultFrontendPort" "vite.config.ts must default frontend port to $DefaultFrontendPort"

foreach ($scriptName in @("backend-check.ps1", "backend-check.sh")) {
    $path = Join-Path $ScriptsDir $scriptName
    $content = Get-Content -Path $path -Raw
    Assert-Contains $content "uv pip check" "$scriptName must run uv pip check"
    Assert-Contains $content "ruff check" "$scriptName must run backend ruff checks"
    Assert-Contains $content "pytest" "$scriptName must run backend pytest"
    Assert-Contains $content "verify-backend-runtime-dependencies.ps1" "$scriptName must run runtime dependency verification"
    Assert-Contains $content "verify-launch-scripts.ps1" "$scriptName must run launch script verification"
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
