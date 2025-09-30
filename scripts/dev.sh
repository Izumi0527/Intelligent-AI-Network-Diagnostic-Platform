#!/bin/bash
# AI智能网络故障分析平台 - 开发环境启动脚本
# 生成时间: 2025-09-07 21:29

set -e  # 遇到错误立即退出

# 输出项目信息
echo "🚀 AI智能网络故障分析平台 - 开发环境启动"
echo "========================================"

# 检查必要目录
if [ ! -d "logs" ]; then
    echo "❌ logs目录不存在，请先运行 scripts/setup.sh"
    exit 1
fi

# 设置环境变量
export APP_ENV=development
export LOG_LEVEL=DEBUG

# 启动后端服务
echo "📦 启动后端服务..."
cd backend

# 检查虚拟环境
if [ -d ".venv" ]; then
    VENV_PATH=".venv"
elif [ -d "venv" ]; then
    VENV_PATH="venv"
    echo "⚠️ 检测到旧版venv目录，建议重命名为.venv"
else
    echo "❌ 未找到虚拟环境，请先创建虚拟环境"
    exit 1
fi

# 激活虚拟环境
if [ "$OS" = "Windows_NT" ]; then
    source "$VENV_PATH/Scripts/activate"
else
    source "$VENV_PATH/bin/activate"
fi

echo "✅ 已激活虚拟环境: $VENV_PATH"

# 启动后端（后台运行）
echo "🔄 启动FastAPI服务器..."
uv run python run.py --reload > ../logs/backend_dev.log 2>&1 &
BACKEND_PID=$!
echo "✅ 后端服务已启动 (PID: $BACKEND_PID)"

# 启动前端服务
echo "📦 启动前端服务..."
cd ../frontend

# 检查依赖是否已安装
if [ ! -d "node_modules" ]; then
    echo "📥 安装前端依赖..."
    npm install
fi

echo "🔄 启动Vite开发服务器..."
npm run dev > ../logs/frontend_dev.log 2>&1 &
FRONTEND_PID=$!

echo "✅ 前端服务已启动 (PID: $FRONTEND_PID)"
echo ""
echo "🎉 服务启动完成！"
echo "========================================"
echo "🌐 前端地址: http://localhost:5173"
echo "🔧 后端API: http://localhost:8000"  
echo "📚 API文档: http://localhost:8000/api/v1/docs"
echo "📋 日志位置: logs/backend_dev.log, logs/frontend_dev.log"
echo ""
echo "💡 按 Ctrl+C 停止所有服务"

# 创建停止函数
cleanup() {
    echo ""
    echo "🔄 停止服务..."
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    echo "✅ 所有服务已停止"
    exit 0
}

# 捕获中断信号
trap cleanup SIGINT SIGTERM

# 等待进程
wait $BACKEND_PID $FRONTEND_PID