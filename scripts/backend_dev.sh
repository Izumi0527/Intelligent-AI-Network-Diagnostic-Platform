#!/bin/bash
# AI智能网络故障分析平台 - 后端开发环境启动脚本
# 生成时间: 2025-09-10

set -e  # 遇到错误立即退出

# 输出项目信息
echo "🚀 AI智能网络故障分析平台 - 后端服务启动"
echo "========================================"

# 检查必要目录
if [ ! -d "../logs" ]; then
    echo "❌ logs目录不存在，请先运行 scripts/setup.sh"
    exit 1
fi

# 设置环境变量
export APP_ENV=development
export LOG_LEVEL=DEBUG

# 进入后端目录
cd "$(dirname "$0")/../backend"

echo "📦 启动后端服务..."

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

echo "✅ 找到虚拟环境: $VENV_PATH"

# 确保依赖已安装
echo "🔄 检查并安装依赖..."
uv pip install fastapi uvicorn pydantic pydantic-settings sse-starlette netmiko aiohttp python-dotenv httpx paramiko python-jose passlib bcrypt requests 2>/dev/null || echo "依赖已存在"

# 启动后端服务
echo "🔄 启动FastAPI服务器..."
uv run python run.py --reload

echo ""
echo "🎉 后端服务启动完成！"
echo "========================================"
echo "🔧 后端API: http://localhost:8000"  
echo "📚 API文档: http://localhost:8000/api/v1/docs"
echo ""
echo "💡 按 Ctrl+C 停止服务"