#!/bin/bash
# AI智能网络故障分析平台 - 构建脚本
# 生成时间: 2025-09-07 21:29

set -e

echo "🔨 AI智能网络故障分析平台 - 生产构建"
echo "========================================"

# 设置构建环境
export NODE_ENV=production
export APP_ENV=production

# 1. 清理之前的构建
echo "🧹 清理构建目录..."
rm -rf frontend/dist
rm -rf backend/dist 
echo "✅ 构建目录已清理"

# 2. 构建前端
echo "📦 构建前端应用..."
cd frontend

# 检查依赖
if [ ! -d "node_modules" ]; then
    echo "📥 安装前端依赖..."
    npm ci  # 生产环境使用ci而不是install
fi

# 类型检查
echo "🔍 执行TypeScript类型检查..."
npm run typecheck || {
    echo "❌ TypeScript类型检查失败"
    exit 1
}

# 构建
echo "🔄 构建前端..."
npm run build || {
    echo "❌ 前端构建失败" 
    exit 1
}

echo "✅ 前端构建完成"
cd ..

# 3. 检查后端依赖
echo "📦 检查后端依赖..."
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

# 4. 运行测试（如果存在）
echo "🧪 运行测试套件..."
if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
    python -m pytest tests/ -v || {
        echo "❌ 测试失败，构建终止"
        exit 1
    }
    echo "✅ 所有测试通过"
else
    echo "⚠️ 未找到测试配置，跳过测试"
fi

cd ..

# 5. 创建部署包
echo "📦 创建部署包..."
BUILD_TIME=$(date +%Y%m%d_%H%M%S)
PACKAGE_NAME="ai-network-platform_${BUILD_TIME}.tar.gz"

tar -czf "dist/${PACKAGE_NAME}" \
    --exclude='backend/.venv' \
    --exclude='backend/venv' \
    --exclude='backend/__pycache__' \
    --exclude='backend/**/__pycache__' \
    --exclude='frontend/node_modules' \
    --exclude='frontend/.vite' \
    --exclude='.git' \
    --exclude='logs' \
    --exclude='discuss' \
    . || {
    echo "❌ 创建部署包失败"
    exit 1
}

echo "✅ 部署包创建完成: dist/${PACKAGE_NAME}"

# 6. 显示构建信息
echo ""
echo "🎉 构建完成！"
echo "========================================"
echo "📦 前端构建: frontend/dist/"
echo "📦 部署包: dist/${PACKAGE_NAME}"
echo "📊 构建信息:"

if [ -d "frontend/dist" ]; then
    DIST_SIZE=$(du -sh frontend/dist | cut -f1)
    echo "   前端包大小: ${DIST_SIZE}"
fi

PACKAGE_SIZE=$(du -sh "dist/${PACKAGE_NAME}" | cut -f1)
echo "   部署包大小: ${PACKAGE_SIZE}"
echo "   构建时间: $(date)"

echo ""
echo "⚡ 部署说明:"
echo "   1. 上传部署包到服务器"
echo "   2. 解压并安装依赖"
echo "   3. 配置环境变量"
echo "   4. 运行 scripts/prod.sh 启动服务"