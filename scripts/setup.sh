#!/bin/bash
# AI智能网络故障分析平台 - 环境初始化脚本
# 生成时间: 2025-09-07 21:29

set -e

echo "🔧 AI智能网络故障分析平台 - 环境初始化"
echo "========================================"

# 1. 创建必要的目录结构
echo "📁 创建目录结构..."

# 创建日志目录
mkdir -p logs/{app,access,error,backend,frontend}

# 创建后端模块目录（为后续重构预备）
mkdir -p backend/app/core/network/{telnet,ssh}
mkdir -p backend/app/core/network/telnet/devices
mkdir -p backend/app/services/ai/{models,deepseek}

echo "✅ 目录结构创建完成"

# 2. 检查并重命名虚拟环境
echo "🔄 检查虚拟环境..."
cd backend

if [ -d "venv" ] && [ ! -d ".venv" ]; then
    echo "📦 重命名 venv → .venv"
    mv venv .venv
    echo "✅ 虚拟环境已重命名"
elif [ -d ".venv" ]; then
    echo "✅ .venv 环境已存在"
else
    echo "❌ 未找到虚拟环境，请手动创建："
    echo "   python -m venv .venv"
    echo "   .venv\\Scripts\\activate  # Windows"
    echo "   source .venv/bin/activate  # Linux/Mac"
    echo "   pip install -r requirements.txt"
fi

cd ..

# 3. 检查前端依赖
echo "📦 检查前端依赖..."
cd frontend

if [ ! -d "node_modules" ]; then
    echo "📥 安装前端依赖..."
    npm install
    echo "✅ 前端依赖安装完成"
else
    echo "✅ 前端依赖已存在"
fi

cd ..

# 4. 创建环境配置文件示例
echo "⚙️ 检查配置文件..."

if [ ! -f "backend/.env" ]; then
    if [ -f "backend/.env.example" ]; then
        echo "📝 复制环境配置模板..."
        cp backend/.env.example backend/.env
        echo "⚠️ 请编辑 backend/.env 文件配置API密钥等参数"
    else
        echo "⚠️ 未找到 .env.example 文件"
    fi
else
    echo "✅ 环境配置文件已存在"
fi

# 5. 设置脚本执行权限
echo "🔐 设置脚本权限..."
chmod +x scripts/*.sh
echo "✅ 脚本权限设置完成"

echo ""
echo "🎉 环境初始化完成！"
echo "========================================"
echo "📂 目录结构:"
echo "   logs/          - 日志文件目录"
echo "   scripts/       - 运行脚本目录"  
echo "   backend/.venv/ - Python虚拟环境"
echo "   frontend/      - 前端项目"
echo ""
echo "⚡ 下一步:"
echo "   1. 编辑 backend/.env 配置文件"
echo "   2. 运行 scripts/dev.sh 启动开发环境"
echo "   3. 运行 scripts/test.sh 执行测试"