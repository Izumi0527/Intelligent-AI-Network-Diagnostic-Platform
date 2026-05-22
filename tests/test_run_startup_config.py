import os
import json
import subprocess
import sys
import textwrap


def test_run_help_bootstraps_development_internal_auth():
    """development 本地启动缺少内部 Token 时，run.py 应先补齐临时配置再加载 Settings。"""
    env = os.environ.copy()
    env.update(
        {
            "APP_ENV": "development",
            "API_PREFIX": "/api",
            "APP_NAME": "AI智能网络故障分析平台",
            "APP_VERSION": "0.1.0",
            "SECRET_KEY": "test-secret-key",
            "JWT_ALGORITHM": "HS256",
            "JWT_ACCESS_TOKEN_EXPIRE_MINUTES": "30",
            "HOST": "127.0.0.1",
            "PORT": "8000",
            "SESSION_IDLE_TIMEOUT": "600",
            "MAX_TERMINAL_SESSIONS": "5",
            "LOG_LEVEL": "INFO",
            "LOG_FORMAT": "standard",
            "AI_ENABLED": "false",
        }
    )
    env.pop("API_AUTH_ENABLED", None)
    env.pop("INTERNAL_API_TOKEN", None)

    result = subprocess.run(
        [sys.executable, "run.py", "--help"],
        cwd="backend",
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0
    assert "非 test 环境必须启用内部 API 鉴权" not in result.stderr
    assert "临时开发内部 API Token" in result.stdout


def test_run_uses_env_file_and_passes_arguments_to_uvicorn(tmp_path):
    """run.py 应加载指定 env 文件，并把启动参数传给 uvicorn.run。"""
    capture_file = tmp_path / "uvicorn-call.json"
    fake_modules = tmp_path / "fake-modules"
    fake_modules.mkdir()
    (fake_modules / "uvicorn.py").write_text(
        textwrap.dedent(
            """
            import json
            import os
            from pathlib import Path


            def run(app, **kwargs):
                payload = {"app": app, **kwargs}
                Path(os.environ["UVICORN_CAPTURE_FILE"]).write_text(
                    json.dumps(payload, ensure_ascii=False),
                    encoding="utf-8",
                )
            """
        ),
        encoding="utf-8",
    )

    env_file = tmp_path / "backend.env"
    env_file.write_text(
        textwrap.dedent(
            """
            APP_ENV=test
            API_PREFIX=/api
            APP_NAME=AI智能网络故障分析平台
            APP_VERSION=0.1.0
            SECRET_KEY=test-secret-key
            JWT_ALGORITHM=HS256
            JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
            HOST=127.0.0.42
            PORT=9123
            SESSION_IDLE_TIMEOUT=600
            MAX_TERMINAL_SESSIONS=5
            LOG_LEVEL=WARNING
            LOG_FORMAT=standard
            AI_ENABLED=false
            """
        ).strip(),
        encoding="utf-8",
    )

    env = os.environ.copy()
    for name in (
        "APP_ENV",
        "API_PREFIX",
        "APP_NAME",
        "APP_VERSION",
        "SECRET_KEY",
        "JWT_ALGORITHM",
        "JWT_ACCESS_TOKEN_EXPIRE_MINUTES",
        "HOST",
        "PORT",
        "SESSION_IDLE_TIMEOUT",
        "MAX_TERMINAL_SESSIONS",
        "LOG_LEVEL",
        "LOG_FORMAT",
        "AI_ENABLED",
        "API_AUTH_ENABLED",
        "INTERNAL_API_TOKEN",
    ):
        env.pop(name, None)
    env["ENV_FILE"] = str(env_file)
    env["UVICORN_CAPTURE_FILE"] = str(capture_file)
    env["PYTHONPATH"] = os.pathsep.join(
        [str(fake_modules), env.get("PYTHONPATH", "")]
    )

    result = subprocess.run(
        [sys.executable, "run.py"],
        cwd="backend",
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(capture_file.read_text(encoding="utf-8"))
    assert payload == {
        "app": "app.main:app",
        "host": "127.0.0.42",
        "port": 9123,
        "reload": False,
        "log_level": "warning",
    }
