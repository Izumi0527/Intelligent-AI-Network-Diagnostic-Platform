#!/usr/bin/env bash
# 后端质量检查脚本：依赖、静态检查、定向测试和脚本契约。
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BACKEND_PATH="$PROJECT_ROOT/backend"
PYTHON_PATH="$BACKEND_PATH/.venv/Scripts/python.exe"

RUFF_TARGETS=(
    "backend/run.py"
    "backend/app/config/settings.py"
    "backend/app/api/deps.py"
    "backend/app/main.py"
    "backend/app/core/rate_limit.py"
    "backend/app/core/network/telnet/client.py"
    "backend/app/core/network/telnet/connection.py"
    "backend/app/core/network/telnet/devices/huawei.py"
    "backend/app/models/ai.py"
    "backend/app/models/terminal.py"
    "backend/app/models/network.py"
    "backend/app/services/terminal_service.py"
    "backend/app/services/terminal_exceptions.py"
    "backend/app/services/ai/base.py"
    "backend/app/services/ai/application_service.py"
    "backend/app/utils/logger.py"
    "backend/app/utils/terminal_policy.py"
    "tests/test_backend_package_metadata.py"
    "tests/test_architecture_boundaries.py"
    "tests/test_pytest_cache_config.py"
    "tests/test_run_startup_config.py"
    "tests/test_pydantic_v2_models.py"
    "tests/test_telnet_login_policy.py"
)

PYTEST_TARGETS=(
    "tests/test_backend_package_metadata.py"
    "tests/test_architecture_boundaries.py"
    "tests/test_pytest_cache_config.py"
    "tests/test_run_startup_config.py"
    "tests/test_pydantic_v2_models.py"
    "tests/test_backend_security_and_connection_policy.py"
    "tests/test_terminal_connection_regressions.py"
    "tests/test_telnet_login_policy.py"
)

write_step() {
    echo "==> $1"
}

if [[ ! -x "$PYTHON_PATH" ]]; then
    echo "缺少后端虚拟环境 Python: $PYTHON_PATH" >&2
    exit 1
fi

write_step "运行 uv pip check"
(cd "$BACKEND_PATH" && uv pip check)

write_step "运行后端依赖声明静态校验"
(cd "$PROJECT_ROOT" && powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "tests/scripts/verify-backend-runtime-dependencies.ps1")

write_step "运行后端定向 ruff check"
(cd "$PROJECT_ROOT" && "$PYTHON_PATH" -m ruff check "${RUFF_TARGETS[@]}")

write_step "运行后端定向 pytest"
(cd "$PROJECT_ROOT" && "$PYTHON_PATH" -m pytest "${PYTEST_TARGETS[@]}" -q --no-cov -p no:cacheprovider)

write_step "运行启动脚本契约校验"
(cd "$PROJECT_ROOT" && powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "tests/scripts/verify-launch-scripts.ps1")

echo "后端质量检查通过。"
