#!/usr/bin/env bash
# AI智能网络故障分析平台 - 前端生产构建脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_PATH="$PROJECT_ROOT/frontend"
DIST_PATH="$FRONTEND_PATH/dist"

write_step() {
    echo "==> $1"
}

ensure_command() {
    local name="$1"
    local hint="$2"
    if ! command -v "$name" >/dev/null 2>&1; then
        echo "缺少命令 $name。$hint" >&2
        exit 1
    fi
}

format_size() {
    local bytes="$1"
    if (( bytes >= 1048576 )); then
        awk -v b="$bytes" 'BEGIN { printf "%.2f MB", b / 1048576 }'
    elif (( bytes >= 1024 )); then
        awk -v b="$bytes" 'BEGIN { printf "%.2f KB", b / 1024 }'
    else
        echo "${bytes} B"
    fi
}

[[ -d "$FRONTEND_PATH" ]] || { echo "前端目录不存在: $FRONTEND_PATH" >&2; exit 1; }
ensure_command "npm" "请先安装 Node.js 和 npm。"

cd "$FRONTEND_PATH"

if [[ ! -d node_modules ]]; then
    write_step "未检测到 node_modules，正在安装前端依赖..."
    npm install
fi

write_step "运行生产构建 (vue-tsc + vite build)"
npm run build

if [[ -d "$DIST_PATH" ]]; then
    total_bytes="$(find "$DIST_PATH" -type f -printf '%s\n' 2>/dev/null | awk '{ sum += $1 } END { print sum+0 }')"
    echo ""
    echo "构建产物体积统计:"
    echo "  dist 目录: $(format_size "$total_bytes")"

    if [[ -d "$DIST_PATH/assets" ]]; then
        while IFS= read -r f; do
            sz="$(stat -c '%s' "$f" 2>/dev/null || stat -f '%z' "$f")"
            echo "  - $(basename "$f"): $(format_size "$sz")"
        done < <(find "$DIST_PATH/assets" -maxdepth 1 -type f)
    fi
fi

echo ""
echo "前端生产构建完成。"
