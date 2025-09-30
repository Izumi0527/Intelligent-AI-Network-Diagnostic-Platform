# AI智能网络故障分析平台 - 生产环境部署脚本
# 生成时间: 2025-09-07 21:29

$ErrorActionPreference = "Stop"

Write-Host "🚀 AI智能网络故障分析平台 - 生产环境部署" -ForegroundColor Green
Write-Host "========================================"

# 设置生产环境变量
$env:APP_ENV = "production"
$env:LOG_LEVEL = "INFO"

# 1. 检查环境
Write-Host "🔍 检查部署环境..."

# 检查必要目录
if (!(Test-Path "logs")) {
    Write-Host "❌ logs目录不存在，请先运行 scripts\setup.ps1" -ForegroundColor Red
    exit 1
}

# 检查配置文件
if (!(Test-Path "backend\.env")) {
    Write-Host "❌ 未找到环境配置文件 backend\.env" -ForegroundColor Red
    exit 1
}

# 检查前端构建文件
if (!(Test-Path "frontend\dist")) {
    Write-Host "❌ 前端未构建，请先运行 scripts\build.ps1" -ForegroundColor Red
    exit 1
}

Write-Host "✅ 部署环境检查通过" -ForegroundColor Green

# 2. 启动后端服务
Write-Host "📦 启动后端服务..."
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

# 启动FastAPI服务（生产模式）
Write-Host "🔄 启动生产服务器..."
$BackendArgs = @(
    "run",
    "python",
    "run.py",
    "--host", "0.0.0.0",
    "--port", "8000"
)

$BackendProcess = Start-Process -FilePath "uv" -ArgumentList $BackendArgs -RedirectStandardOutput "..\logs\backend_prod.log" -RedirectStandardError "..\logs\backend_prod.log" -PassThru -WindowStyle Hidden

$BackendPID = $BackendProcess.Id
$BackendPID | Out-File -FilePath "..\logs\backend.pid" -Encoding UTF8

Write-Host "✅ 后端服务已启动 (PID: $BackendPID)" -ForegroundColor Green
Set-Location ..

# 3. 检查Web服务器配置（如果使用IIS）
if (Get-WindowsFeature -Name IIS-WebServerRole -ErrorAction SilentlyContinue | Where-Object { $_.InstallState -eq "Installed" }) {
    Write-Host "🌐 检测到IIS，检查站点配置..."
    
    # 检查是否存在应用程序池和站点配置
    $SiteName = "AI-Network-Platform"
    try {
        Import-Module WebAdministration -ErrorAction SilentlyContinue
        $Site = Get-Website -Name $SiteName -ErrorAction SilentlyContinue
        if ($Site) {
            Write-Host "✅ IIS站点配置已存在" -ForegroundColor Green
        } else {
            Write-Host "⚠️ 未配置IIS站点，前端需手动配置" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "⚠️ 无法检查IIS配置，请手动验证" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️ 未安装IIS，前端静态文件需配置其他Web服务器" -ForegroundColor Yellow
}

# 4. 健康检查
Write-Host "🔍 执行健康检查..."
Start-Sleep -Seconds 5  # 等待服务启动

# 检查后端API
$HealthCheckUrl = "http://localhost:8000/api/v1/health"
try {
    $Response = Invoke-RestMethod -Uri $HealthCheckUrl -TimeoutSec 10
    Write-Host "✅ 后端API健康检查通过" -ForegroundColor Green
} catch {
    Write-Host "❌ 后端API健康检查失败: $($_.Exception.Message)" -ForegroundColor Red
    
    # 检查进程是否还在运行
    if (Get-Process -Id $BackendPID -ErrorAction SilentlyContinue) {
        Write-Host "⚠️ 后端进程运行中，但API无响应" -ForegroundColor Yellow
    } else {
        Write-Host "❌ 后端进程已退出" -ForegroundColor Red
    }
    
    exit 1
}

# 5. 显示部署信息
Write-Host ""
Write-Host "🎉 部署完成！" -ForegroundColor Green
Write-Host "========================================"
Write-Host "🔧 后端服务: http://localhost:8000" -ForegroundColor Cyan
Write-Host "📚 API文档: http://localhost:8000/api/v1/docs" -ForegroundColor Cyan
Write-Host "📋 日志文件:" -ForegroundColor Cyan
Write-Host "   后端日志: logs\backend_prod.log"
Write-Host "   访问日志: logs\access\"
Write-Host "   错误日志: logs\error\"
Write-Host "📊 进程信息:" -ForegroundColor Cyan
Write-Host "   后端PID: $BackendPID (保存在 logs\backend.pid)"
Write-Host ""
Write-Host "🛠️ 管理命令:" -ForegroundColor Yellow
Write-Host "   停止服务: Stop-Process -Id $BackendPID"
Write-Host "   查看日志: Get-Content logs\backend_prod.log -Tail 50 -Wait"
Write-Host "   检查进程: Get-Process -Id $BackendPID"
Write-Host "   健康检查: Invoke-RestMethod http://localhost:8000/api/v1/health"

# 6. 创建停止脚本
$StopScriptContent = @"
# 停止AI网络平台生产服务
`$ErrorActionPreference = "Stop"

Write-Host "🔄 停止AI网络平台服务..." -ForegroundColor Yellow

if (Test-Path "logs\backend.pid") {
    `$BackendPID = Get-Content "logs\backend.pid" -Raw
    `$BackendPID = `$BackendPID.Trim()
    
    if (`$BackendPID -and (Get-Process -Id `$BackendPID -ErrorAction SilentlyContinue)) {
        Stop-Process -Id `$BackendPID -Force
        Write-Host "✅ 后端服务已停止 (PID: `$BackendPID)" -ForegroundColor Green
        Remove-Item "logs\backend.pid" -Force
    } else {
        Write-Host "⚠️ 后端进程不存在或已停止" -ForegroundColor Yellow
    }
} else {
    Write-Host "⚠️ 未找到进程ID文件" -ForegroundColor Yellow
}

Write-Host "🎉 服务停止完成" -ForegroundColor Green
"@

$StopScriptContent | Out-File -FilePath "scripts\stop.ps1" -Encoding UTF8
Write-Host ""
Write-Host "📝 已创建停止脚本: scripts\stop.ps1" -ForegroundColor Green

# 7. 设置Windows服务（可选，需要管理员权限）
Write-Host ""
Write-Host "💡 生产环境建议:" -ForegroundColor Cyan
Write-Host "   1. 配置Windows服务自动启动"
Write-Host "   2. 设置防火墙规则开放8000端口"
Write-Host "   3. 配置负载均衡器或反向代理"
Write-Host "   4. 设置监控和告警"
Write-Host "   5. 配置SSL证书（HTTPS）"