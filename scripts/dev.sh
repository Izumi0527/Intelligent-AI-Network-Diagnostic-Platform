#!/usr/bin/env bash
# AI智能网络故障分析平台 - 开发环境统一启动脚本
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_PATH="$PROJECT_ROOT/backend"
FRONTEND_PATH="$PROJECT_ROOT/frontend"
LOGS_PATH="$PROJECT_ROOT/logs"
DEVELOPMENT_INTERNAL_API_TOKEN=""

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
BACKEND_TIMEOUT_SECONDS="${BACKEND_TIMEOUT_SECONDS:-90}"
SKIP_FRONTEND_INSTALL="${SKIP_FRONTEND_INSTALL:-0}"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --backend-host)
            BACKEND_HOST="$2"
            shift 2
            ;;
        --backend-port)
            BACKEND_PORT="$2"
            shift 2
            ;;
        --frontend-host)
            FRONTEND_HOST="$2"
            shift 2
            ;;
        --frontend-port)
            FRONTEND_PORT="$2"
            shift 2
            ;;
        --backend-timeout)
            BACKEND_TIMEOUT_SECONDS="$2"
            shift 2
            ;;
        --skip-frontend-install)
            SKIP_FRONTEND_INSTALL="1"
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

shell_quote() {
    printf "%q" "$1"
}

health_host() {
    case "$1" in
        "0.0.0.0"|"::"|"[::]")
            echo "127.0.0.1"
            ;;
        *)
            echo "$1"
            ;;
    esac
}

ensure_command() {
    local name="$1"
    local hint="$2"

    if ! command -v "$name" >/dev/null 2>&1; then
        echo "缺少命令 $name。$hint" >&2
        exit 1
    fi
}

ensure_project_layout() {
    [[ -d "$BACKEND_PATH" ]] || { echo "后端目录不存在: $BACKEND_PATH" >&2; exit 1; }
    [[ -d "$FRONTEND_PATH" ]] || { echo "前端目录不存在: $FRONTEND_PATH" >&2; exit 1; }
    [[ -f "$BACKEND_PATH/.env" ]] || { echo "缺少 backend/.env，请先从 backend/.env.example 复制并填写配置。" >&2; exit 1; }

    mkdir -p "$LOGS_PATH/app" "$LOGS_PATH/access" "$LOGS_PATH/error" "$LOGS_PATH/backend" "$LOGS_PATH/frontend"
}

read_env_value() {
    local name="$1"
    local line
    while IFS= read -r line; do
        case "$line" in
            "$name="*)
                line="${line#*=}"
                line="${line%\"}"
                line="${line#\"}"
                line="${line%\'}"
                line="${line#\'}"
                printf "%s" "$line"
                return 0
                ;;
        esac
    done < "$BACKEND_PATH/.env"
    return 1
}

invalid_internal_api_token() {
    local token="${1:-}"
    case "${token,,}" in
        ""|"change-me"|"change-me-internal-api-token"|"your-token"|"test-token")
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

new_urlsafe_token() {
    if command -v python3 >/dev/null 2>&1; then
        python3 -c 'import secrets; print(secrets.token_urlsafe(32))'
    elif command -v python >/dev/null 2>&1; then
        python -c 'import secrets; print(secrets.token_urlsafe(32))'
    elif command -v openssl >/dev/null 2>&1; then
        openssl rand -base64 32 | tr '+/' '-_' | tr -d '='
    else
        echo "缺少 python 或 openssl，无法生成开发内部 API Token。" >&2
        exit 1
    fi
}

development_internal_api_token() {
    local configured_token
    configured_token="$(read_env_value "INTERNAL_API_TOKEN" || true)"
    if ! invalid_internal_api_token "$configured_token"; then
        printf "%s" "$configured_token"
        return 0
    fi

    echo "未检测到可用 INTERNAL_API_TOKEN，已生成仅本次开发会话使用的临时 Token。" >&2
    new_urlsafe_token
}

escape_osascript() {
    printf "%s" "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

start_managed_window() {
    local role="$1"
    local title="$2"
    local working_directory="$3"
    local command_body="$4"
    local quoted_workdir
    local full_command
    local quoted_full_command
    quoted_workdir="$(shell_quote "$working_directory")"
    full_command="cd $quoted_workdir; $command_body; exec bash"
    quoted_full_command="$(shell_quote "$full_command")"

    write_step "弹出 $role 窗口: $title"

    if [[ "$(uname -s)" == "Darwin" ]] && command -v osascript >/dev/null 2>&1; then
        local escaped_title
        local escaped_command
        escaped_title="$(escape_osascript "$title")"
        escaped_command="$(escape_osascript "printf '\033]0;${title}\007'; cd $quoted_workdir; $command_body; exec bash")"
        osascript >/dev/null <<OSA
tell application "Terminal"
    do script "$escaped_command"
    set custom title of front window to "$escaped_title"
    activate
end tell
OSA
    elif command -v gnome-terminal >/dev/null 2>&1; then
        gnome-terminal --title="$title" -- bash -lc "$full_command"
    elif command -v konsole >/dev/null 2>&1; then
        konsole --new-tab --workdir "$working_directory" -p tabtitle="$title" -e bash -lc "$command_body; exec bash"
    elif command -v xfce4-terminal >/dev/null 2>&1; then
        xfce4-terminal --title="$title" --working-directory="$working_directory" --command="bash -lc $quoted_full_command"
    elif command -v xterm >/dev/null 2>&1; then
        xterm -T "$title" -e bash -lc "$full_command" &
    else
        echo "未找到可弹出的终端模拟器，请安装 Terminal、gnome-terminal、konsole、xfce4-terminal 或 xterm。" >&2
        exit 1
    fi
}

wait_backend_ready() {
    local url="$1"
    local timeout_seconds="$2"
    local deadline=$((SECONDS + timeout_seconds))
    local last_error=""

    write_step "等待后端健康检查: $url"

    while (( SECONDS < deadline )); do
        if curl -fsS --max-time 3 "$url" >/dev/null 2>&1; then
            echo "后端已正常启动。"
            return 0
        fi

        last_error="curl $url 失败"
        sleep 2
    done

    echo "后端在 ${timeout_seconds} 秒内未通过健康检查。最后错误: $last_error" >&2
    exit 1
}

new_backend_command() {
    printf "export APP_ENV=development; export API_AUTH_ENABLED=true; export INTERNAL_API_TOKEN=%s; export LOG_LEVEL=DEBUG; export PYTHONDONTWRITEBYTECODE=1; echo '后端开发服务启动中...'; uv run python run.py --host %s --port %s --reload" \
        "$(shell_quote "$DEVELOPMENT_INTERNAL_API_TOKEN")" \
        "$(shell_quote "$BACKEND_HOST")" \
        "$(shell_quote "$BACKEND_PORT")"
}

new_frontend_command() {
    local install_command
    if [[ "$SKIP_FRONTEND_INSTALL" == "1" ]]; then
        install_command="echo '已跳过前端依赖自动安装。'"
    else
        install_command="if [ ! -d node_modules ]; then echo '未检测到 node_modules，正在安装前端依赖...'; npm install; fi"
    fi

    printf "export NODE_ENV=development; export VITE_INTERNAL_API_TOKEN=%s; %s; vite_bin='./node_modules/.bin/vite'; if [ ! -x \"\$vite_bin\" ]; then echo '未找到本地 Vite 可执行文件，请确认前端依赖安装成功。' >&2; exit 1; fi; echo '前端开发服务启动中...'; \"\$vite_bin\" --host %s --port %s" \
        "$(shell_quote "$DEVELOPMENT_INTERNAL_API_TOKEN")" \
        "$install_command" \
        "$(shell_quote "$FRONTEND_HOST")" \
        "$(shell_quote "$FRONTEND_PORT")"
}

echo "AI智能网络故障分析平台 - 开发环境启动"
echo "项目路径: $PROJECT_ROOT"

ensure_project_layout
ensure_command "uv" "请先安装 uv: https://github.com/astral-sh/uv"
ensure_command "npm" "请先安装 Node.js 和 npm。"
ensure_command "curl" "请先安装 curl。"
DEVELOPMENT_INTERNAL_API_TOKEN="$(development_internal_api_token)"

HEALTH_HOST="$(health_host "$BACKEND_HOST")"
HEALTH_URL="http://${HEALTH_HOST}:${BACKEND_PORT}/api/v1/health"

start_managed_window "backend" "AI Network Backend Dev :$BACKEND_PORT" "$BACKEND_PATH" "$(new_backend_command)"
wait_backend_ready "$HEALTH_URL" "$BACKEND_TIMEOUT_SECONDS"
start_managed_window "frontend" "AI Network Frontend Dev :$FRONTEND_PORT" "$FRONTEND_PATH" "$(new_frontend_command)"

echo ""
echo "开发环境启动流程已完成。"
echo "后端: http://${HEALTH_HOST}:${BACKEND_PORT}"
echo "前端: http://127.0.0.1:${FRONTEND_PORT}"
