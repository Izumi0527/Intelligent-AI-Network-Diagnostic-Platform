import os
import subprocess
import sys
from pathlib import Path


def test_project_python_startup_disables_bytecode_writes(tmp_path):
    """从项目入口启动 Python 时应默认禁止写入 __pycache__ 和 pyc。"""
    project_root = Path(__file__).resolve().parents[1]
    launch_dirs = [project_root, project_root / "backend"]

    for launch_dir in launch_dirs:
        module_dir = tmp_path / f"module_{launch_dir.name}"
        module_dir.mkdir()
        (module_dir / "probe_module.py").write_text("VALUE = 42\n", encoding="utf-8")

        env = os.environ.copy()
        env.pop("PYTHONDONTWRITEBYTECODE", None)
        env["PYTHONPATH"] = str(module_dir)

        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; import probe_module; print(int(sys.dont_write_bytecode))",
            ],
            cwd=launch_dir,
            env=env,
            text=True,
            capture_output=True,
            check=False,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == "1"
        assert not (launch_dir / "__pycache__").exists()
        assert not (module_dir / "__pycache__").exists()


def test_python_cache_cleaners_include_virtual_environment_caches():
    """缓存清理脚本不能跳过虚拟环境内的 pyc 历史缓存。"""
    project_root = Path(__file__).resolve().parents[1]
    powershell_cleaner = (
        project_root / "scripts" / "clean-python-cache.ps1"
    ).read_text(encoding="utf-8")
    shell_cleaner = (
        project_root / "scripts" / "clean-python-cache.sh"
    ).read_text(encoding="utf-8")

    assert '".venv"' not in powershell_cleaner
    assert '"venv"' not in powershell_cleaner
    assert '-name ".venv"' not in shell_cleaner
    assert '-name "venv"' not in shell_cleaner
