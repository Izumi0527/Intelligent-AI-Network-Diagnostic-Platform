#!/usr/bin/env bash
# AI智能网络故障分析平台 - 前端 lint + typecheck 检查脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
FRONTEND_PATH="$PROJECT_ROOT/frontend"

FIX_MODE="0"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --fix)
            FIX_MODE="1"
            shift
            ;;
        *)
            echo "未知参数: $1" >&2
            exit 1
            ;;
    esac
done

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

[[ -d "$FRONTEND_PATH" ]] || { echo "前端目录不存在: $FRONTEND_PATH" >&2; exit 1; }
ensure_command "npm" "请先安装 Node.js 和 npm。"

cd "$FRONTEND_PATH"

if [[ ! -d node_modules ]]; then
    write_step "未检测到 node_modules，正在安装前端依赖..."
    npm install
fi

write_step "运行 TypeScript 类型检查 (vue-tsc --noEmit)"
npm run typecheck

if [[ "$FIX_MODE" == "1" ]]; then
    write_step "运行 ESLint --fix"
    npm run lint:fix
else
    write_step "运行 ESLint"
    npm run lint
fi

echo ""
echo "类型检查与 lint 全部通过。"
