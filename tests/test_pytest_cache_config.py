from pathlib import Path


def test_pytest_cache_is_configured_under_tests_directory():
    """pytest 缓存应固定写入 tests/.pytest_cache，避免污染项目根目录和后端目录。"""
    project_root = Path(__file__).resolve().parents[1]

    root_pytest_config = (project_root / "pytest.ini").read_text(encoding="utf-8")
    backend_pytest_config = (project_root / "backend" / "pyproject.toml").read_text(
        encoding="utf-8"
    )

    assert "cache_dir = tests/.pytest_cache" in root_pytest_config
    assert 'cache_dir = "../tests/.pytest_cache"' in backend_pytest_config
