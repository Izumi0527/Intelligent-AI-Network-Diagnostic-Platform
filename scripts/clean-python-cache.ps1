# 清理项目内 Python 字节码缓存目录和文件
[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot)
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ResolvedProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$ExcludedDirectoryNames = @(".git", "node_modules")

function Get-PythonCacheItem {
    param([string]$Directory)

    $children = Get-ChildItem -LiteralPath $Directory -Force -ErrorAction SilentlyContinue
    foreach ($child in $children) {
        if ($child.PSIsContainer) {
            if ($child.Name -in $ExcludedDirectoryNames) {
                continue
            }

            if ($child.Name -eq "__pycache__") {
                [pscustomobject]@{
                    Type = "Directory"
                    Path = $child.FullName
                }
                continue
            }

            Get-PythonCacheItem -Directory $child.FullName
            continue
        }

        if ($child.Extension -in @(".pyc", ".pyo")) {
            [pscustomobject]@{
                Type = "File"
                Path = $child.FullName
            }
        }
    }
}

$items = @(Get-PythonCacheItem -Directory $ResolvedProjectRoot)
$bytecodeFiles = @($items | Where-Object { $_.Type -eq "File" })
$cacheDirectories = @($items | Where-Object { $_.Type -eq "Directory" } | Sort-Object { $_.Path.Length } -Descending)

foreach ($file in $bytecodeFiles) {
    if ($PSCmdlet.ShouldProcess($file.Path, "删除 Python 字节码文件")) {
        Remove-Item -LiteralPath $file.Path -Force -ErrorAction SilentlyContinue
    }
}

foreach ($directory in $cacheDirectories) {
    if ($PSCmdlet.ShouldProcess($directory.Path, "删除 Python 缓存目录")) {
        Remove-Item -LiteralPath $directory.Path -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Host "Python 缓存清理完成。" -ForegroundColor Green
Write-Host "项目路径: $ResolvedProjectRoot"
Write-Host "已删除 __pycache__ 目录: $($cacheDirectories.Count)"
Write-Host "已删除 .pyc/.pyo 文件: $($bytecodeFiles.Count)"
