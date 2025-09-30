#!/bin/bash
# AI智能网络故障分析平台 - 生产环境部署脚本
# 生成时间: 2025-09-07 21:29

set -e

echo "🚀 AI智能网络故障分析平台 - 生产环境部署"
echo "========================================"

# 设置生产环境变量
export APP_ENV=production
export LOG_LEVEL=INFO

# 1. 检查环境
echo "🔍 检查部署环境..."

# 检查必要目录
if [ ! -d "logs" ]; then
    echo "❌ logs目录不存在，请先运行 scripts/setup.sh"
    exit 1
fi

# 检查配置文件
if [ ! -f "backend/.env" ]; then
    echo "❌ 未找到环境配置文件 backend/.env"
    exit 1
fi

# 检查前端构建文件
if [ ! -d "frontend/dist" ]; then
    echo "❌ 前端未构建，请先运行 scripts/build.sh"
    exit 1
fi

echo "✅ 部署环境检查通过"

# 2. 启动后端服务
echo "📦 启动后端服务..."
cd backend

# 激活虚拟环境
if [ -d ".venv" ]; then
    VENV_PATH=".venv"
elif [ -d "venv" ]; then
    VENV_PATH="venv"
else
    echo "❌ 未找到虚拟环境"
    exit 1
fi

if [ "$OS" = "Windows_NT" ]; then
    source "$VENV_PATH/Scripts/activate"
else
    source "$VENV_PATH/bin/activate"
fi

echo "✅ 已激活虚拟环境"

# 启动FastAPI服务（生产模式）
echo "🔄 启动生产服务器..."
nohup python run.py \
    --host 0.0.0.0 \
    --port 8000 \
    > ../logs/backend_prod.log 2>&1 &

BACKEND_PID=$!
echo $BACKEND_PID > ../logs/backend.pid

echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"
cd ..

# 3. 启动Nginx（如果配置了）
if command -v nginx &> /dev/null && [ -f "/etc/nginx/sites-available/ai-network-platform" ]; then
    echo "🌐 启动Nginx反向代理..."
    sudo nginx -s reload
    echo "✅ Nginx配置已重载"
else
    echo "⚠️ 未配置Nginx，前端静态文件需手动配置web服务器"
fi

# 4. 健康检查
echo "🔍 执行健康检查..."
sleep 5  # 等待服务启动

# 检查后端API
if curl -s http://localhost:8000/api/v1/health > /dev/null; then
    echo "✅ 后端API健康检查通过"
else
    echo "❌ 后端API健康检查失败"
    exit 1
fi

# 5. 显示部署信息
echo ""
echo "🎉 部署完成！"
echo "========================================"
echo "🔧 后端服务: http://localhost:8000"
echo "📚 API文档: http://localhost:8000/api/v1/docs"
echo "📋 日志文件:"
echo "   后端日志: logs/backend_prod.log"
echo "   访问日志: logs/access/"
echo "   错误日志: logs/error/"
echo "📊 进程信息:"
echo "   后端PID: $BACKEND_PID (保存在 logs/backend.pid)"
echo ""
echo "🛠️ 管理命令:"
echo "   停止服务: scripts/stop.sh"
echo "   查看日志: tail -f logs/backend_prod.log"
echo "   重启服务: scripts/restart.sh"
echo "   健康检查: curl http://localhost:8000/api/v1/health"

# 6. 设置日志轮转（如果支持logrotate）
if command -v logrotate &> /dev/null; then
    echo "📝 配置日志轮转..."
    # 这里可以添加logrotate配置
fi