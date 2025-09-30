#!/bin/bash
# AI智能网络故障分析平台 - 代码质量检查脚本
# 生成时间: 2025-09-07 21:29

set -e

echo "🔍 AI智能网络故障分析平台 - 代码质量检查"
echo "========================================"

# 初始化检查结果
PYTHON_ISSUES=0
FRONTEND_ISSUES=0
FILE_LENGTH_ISSUES=0

# 1. Python代码检查
echo "🐍 检查Python代码质量..."
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

# 代码格式检查
echo "📝 检查代码格式..."
if command -v black &> /dev/null; then
    if ! black --check app/; then
        echo "⚠️ 代码格式需要修复，运行: black app/"
        ((PYTHON_ISSUES++))
    fi
else
    echo "💡 建议安装black进行代码格式检查: pip install black"
fi

# 代码质量检查
echo "🔎 检查代码质量..."
if command -v ruff &> /dev/null; then
    if ! ruff check app/; then
        echo "⚠️ 发现代码质量问题"
        ((PYTHON_ISSUES++))
    fi
elif command -v flake8 &> /dev/null; then
    if ! flake8 app/; then
        echo "⚠️ 发现代码质量问题"
        ((PYTHON_ISSUES++))
    fi
else
    echo "💡 建议安装ruff进行代码质量检查: pip install ruff"
fi

# 类型检查
echo "🏷️ 检查类型注解..."
if command -v mypy &> /dev/null; then
    if ! mypy app/; then
        echo "⚠️ 发现类型检查问题"
        ((PYTHON_ISSUES++))
    fi
else
    echo "💡 建议安装mypy进行类型检查: pip install mypy"
fi

cd ..

# 2. 前端代码检查
echo ""
echo "🌐 检查前端代码质量..."
cd frontend

# TypeScript类型检查
echo "🏷️ 检查TypeScript类型..."
if ! npm run typecheck; then
    echo "❌ TypeScript类型检查失败"
    ((FRONTEND_ISSUES++))
fi

# ESLint检查（如果配置了）
echo "📋 检查代码规范..."
if [ -f ".eslintrc.js" ] || [ -f ".eslintrc.json" ] || [ -f "eslint.config.js" ]; then
    if command -v eslint &> /dev/null || npm list eslint &> /dev/null; then
        if ! npm run lint 2>/dev/null; then
            echo "⚠️ ESLint检查发现问题"
            ((FRONTEND_ISSUES++))
        fi
    fi
else
    echo "💡 建议配置ESLint进行代码规范检查"
fi

cd ..

# 3. 文件长度检查（重点检查）
echo ""
echo "📏 检查文件长度合规性..."
echo "规则：Python文件≤300行，TypeScript/Vue文件≤300行"

# Python文件长度检查
echo ""
echo "🐍 Python文件长度检查："
find backend -name "*.py" -not -path "*/venv/*" -not -path "*/.venv/*" -not -path "*/__pycache__/*" | while read file; do
    lines=$(wc -l < "$file")
    if [ $lines -gt 300 ]; then
        echo "❌ $file: $lines 行 (超过300行限制 $(((lines-300)*100/300))%)"
        ((FILE_LENGTH_ISSUES++))
    elif [ $lines -gt 250 ]; then
        echo "⚠️ $file: $lines 行 (接近300行限制)"
    fi
done

# 前端文件长度检查
echo ""
echo "🌐 前端文件长度检查："
find frontend/src -name "*.vue" -o -name "*.ts" -o -name "*.js" | while read file; do
    lines=$(wc -l < "$file")
    if [ $lines -gt 300 ]; then
        echo "❌ $file: $lines 行 (超过300行限制 $(((lines-300)*100/300))%)"
        ((FILE_LENGTH_ISSUES++))
    elif [ $lines -gt 250 ]; then
        echo "⚠️ $file: $lines 行 (接近300行限制)"
    fi
done

# 4. 目录结构检查
echo ""
echo "📁 检查目录结构..."

# 检查必要目录
REQUIRED_DIRS=("scripts" "logs" "docs" "backend/app" "frontend/src")
for dir in "${REQUIRED_DIRS[@]}"; do
    if [ ! -d "$dir" ]; then
        echo "❌ 缺少必要目录: $dir"
    else
        echo "✅ $dir"
    fi
done

# 检查每层文件数量
echo ""
echo "📊 检查目录文件数量（每层建议≤8个）："
find . -type d -not -path "./.git/*" -not -path "./backend/venv/*" -not -path "./backend/.venv/*" -not -path "./frontend/node_modules/*" | while read dir; do
    count=$(find "$dir" -maxdepth 1 -type f | wc -l)
    if [ $count -gt 8 ]; then
        echo "⚠️ $dir: $count 个文件 (建议≤8个)"
    fi
done

# 5. 总结报告
echo ""
echo "📊 检查结果汇总"
echo "========================================"

if [ $PYTHON_ISSUES -eq 0 ]; then
    echo "✅ Python代码质量: 优秀"
else
    echo "⚠️ Python代码问题: $PYTHON_ISSUES 个"
fi

if [ $FRONTEND_ISSUES -eq 0 ]; then
    echo "✅ 前端代码质量: 优秀" 
else
    echo "⚠️ 前端代码问题: $FRONTEND_ISSUES 个"
fi

# 文件长度问题需要特别统计
LONG_FILES=$(find backend -name "*.py" -not -path "*venv*" -exec wc -l {} \; | awk '$1 > 300 {count++} END {print count+0}')
LONG_FRONTEND=$(find frontend/src -name "*.vue" -o -name "*.ts" -o -name "*.js" -exec wc -l {} \; | awk '$1 > 300 {count++} END {print count+0}')
TOTAL_LONG_FILES=$((LONG_FILES + LONG_FRONTEND))

if [ $TOTAL_LONG_FILES -eq 0 ]; then
    echo "✅ 文件长度: 全部合规"
else
    echo "❌ 超长文件: $TOTAL_LONG_FILES 个需要重构"
fi

echo ""
if [ $((PYTHON_ISSUES + FRONTEND_ISSUES + TOTAL_LONG_FILES)) -eq 0 ]; then
    echo "🎉 代码质量检查全部通过！"
    exit 0
else
    echo "⚠️ 发现 $((PYTHON_ISSUES + FRONTEND_ISSUES + TOTAL_LONG_FILES)) 个问题需要处理"
    echo ""
    echo "💡 改进建议："
    if [ $TOTAL_LONG_FILES -gt 0 ]; then
        echo "   1. 拆分超长文件（优先级最高）"
    fi
    if [ $PYTHON_ISSUES -gt 0 ]; then
        echo "   2. 修复Python代码问题"
    fi
    if [ $FRONTEND_ISSUES -gt 0 ]; then
        echo "   3. 修复前端代码问题"
    fi
    exit 1
fi