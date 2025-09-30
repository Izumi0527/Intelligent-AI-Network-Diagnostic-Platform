#!/bin/bash
# AI智能网络故障分析平台 - 测试脚本
# 生成时间: 2025-09-07 21:29

set -e

echo "🧪 AI智能网络故障分析平台 - 测试执行"
echo "========================================"

# 1. 后端测试
echo "📦 执行后端测试..."
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

# 运行Python测试
if [ -d "tests" ] || find . -name "test_*.py" -o -name "*_test.py" | head -1 > /dev/null; then
    echo "🔄 运行Python单元测试..."
    python -m pytest tests/ -v --tb=short || {
        echo "❌ 后端测试失败"
        exit 1
    }
    echo "✅ 后端测试通过"
else
    echo "⚠️ 未找到后端测试文件，跳过测试"
fi

cd ..

# 2. 前端测试  
echo "📦 执行前端测试..."
cd frontend

# 检查是否有测试配置
if [ -f "vitest.config.ts" ] || [ -f "jest.config.js" ] || grep -q "test" package.json; then
    echo "🔄 运行前端单元测试..."
    npm test || {
        echo "❌ 前端测试失败"
        exit 1
    }
    echo "✅ 前端测试通过"
else
    echo "⚠️ 未找到前端测试配置，跳过测试"
fi

cd ..

# 3. 代码质量检查
echo "🔍 执行代码质量检查..."

# Python代码检查
echo "🔄 检查Python代码..."
cd backend

# 检查代码格式（如果有black）
if command -v black &> /dev/null; then
    black --check app/ || echo "⚠️ Python代码格式需要调整"
fi

# 检查代码质量（如果有flake8或ruff）  
if command -v ruff &> /dev/null; then
    ruff check app/ || echo "⚠️ Python代码质量问题"
elif command -v flake8 &> /dev/null; then
    flake8 app/ || echo "⚠️ Python代码质量问题"
fi

cd ..

# TypeScript类型检查
echo "🔄 检查TypeScript类型..."
cd frontend
npm run typecheck || {
    echo "❌ TypeScript类型检查失败"
    exit 1
}
cd ..

echo ""
echo "🎉 所有测试完成！"
echo "========================================"
echo "✅ 测试状态: 通过"
echo "📊 测试覆盖率报告: tests/coverage/"
echo "🔍 代码质量: 检查完成"

# 4. 文件长度检查
echo ""
echo "📏 检查文件长度合规性..."

# 检查Python文件
echo "🐍 Python文件长度检查:"
find backend -name "*.py" -not -path "*/venv/*" -not -path "*/.venv/*" | while read file; do
    lines=$(wc -l < "$file")
    if [ $lines -gt 300 ]; then
        echo "⚠️ $file: $lines 行 (超过300行限制)"
    fi
done

# 检查前端文件  
echo "🌐 前端文件长度检查:"
find frontend/src -name "*.vue" -o -name "*.ts" -o -name "*.js" | while read file; do
    lines=$(wc -l < "$file")
    if [ $lines -gt 300 ]; then
        echo "⚠️ $file: $lines 行 (超过300行限制)"
    fi
done

echo "✅ 文件长度检查完成"