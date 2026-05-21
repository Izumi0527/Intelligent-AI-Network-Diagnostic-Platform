#!/usr/bin/env bash
# 清理项目内 Python 字节码缓存目录和文件
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

mapfile -d '' bytecode_files < <(
    find "$PROJECT_ROOT" \
        \( -type d \( -name ".git" -o -name "node_modules" \) \) -prune -o \
        -type f \( -name "*.pyc" -o -name "*.pyo" \) -print0
)

mapfile -d '' cache_dirs < <(
    find "$PROJECT_ROOT" \
        \( -type d \( -name ".git" -o -name "node_modules" \) \) -prune -o \
        -type d -name "__pycache__" -print0
)

for file in "${bytecode_files[@]}"; do
    rm -f "$file"
done

for directory in "${cache_dirs[@]}"; do
    rm -rf "$directory"
done

echo "Python 缓存清理完成。"
echo "项目路径: $PROJECT_ROOT"
echo "已删除 __pycache__ 目录: ${#cache_dirs[@]}"
echo "已删除 .pyc/.pyo 文件: ${#bytecode_files[@]}"
