from pathlib import Path
import re


def _backend_paths():
    project_root = Path(__file__).resolve().parents[1]
    backend_root = project_root / "backend"
    return backend_root, backend_root / "pyproject.toml", backend_root / "uv.lock"


def _project_section(pyproject_text: str) -> str:
    project_section = re.search(
        r"(?ms)^\[project\]\s*(.*?)(?=^\[|\Z)",
        pyproject_text,
    )
    assert project_section is not None
    return project_section.group(1)


def _project_runtime_dependencies(pyproject_text: str) -> list[str]:
    dependencies = re.search(
        r"(?ms)^dependencies\s*=\s*\[\s*(.*?)^\]\s*$",
        _project_section(pyproject_text),
    )
    assert dependencies is not None
    return re.findall(r'"([^"]+)"', dependencies.group(1))


def test_backend_package_readme_metadata_is_resolvable():
    """后端包元数据声明的 readme 必须能被 hatchling 构建后端解析。"""
    _, pyproject_path, _ = _backend_paths()
    pyproject_text = pyproject_path.read_text(encoding="utf-8")

    readme = re.search(r'(?m)^readme\s*=\s*"([^"]+)"\s*$', _project_section(pyproject_text))
    assert readme is not None
    assert (pyproject_path.parent / readme.group(1)).resolve().is_file()


def test_backend_python_version_bounds_match_telnetlib_plan():
    """替换 telnetlib 前，后端包声明必须排除 Python 3.13 及以上。"""
    _, pyproject_path, lock_path = _backend_paths()
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    lock_text = lock_path.read_text(encoding="utf-8")

    pyproject_requires_python = re.search(
        r'(?m)^requires-python\s*=\s*"([^"]+)"\s*$',
        pyproject_text,
    )
    lock_requires_python = re.search(
        r'(?m)^requires-python\s*=\s*"([^"]+)"\s*$',
        lock_text,
    )

    assert pyproject_requires_python is not None
    assert lock_requires_python is not None
    assert pyproject_requires_python.group(1).replace(" ", "") == ">=3.9,<3.13"
    assert lock_requires_python.group(1).replace(" ", "") == ">=3.9,<3.13"


def test_requirements_file_is_marked_generated_and_synced():
    """requirements.txt 只能作为生成产物，依赖权威来源是 pyproject 与 uv.lock。"""
    backend_root, pyproject_path, _ = _backend_paths()
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    requirements_lines = (backend_root / "requirements.txt").read_text(
        encoding="utf-8"
    ).splitlines()

    assert requirements_lines[0].startswith(
        "# Generated from backend/pyproject.toml and backend/uv.lock"
    )

    concrete_requirements = [
        line.strip()
        for line in requirements_lines
        if line.strip() and not line.lstrip().startswith("#")
    ]
    assert concrete_requirements == _project_runtime_dependencies(pyproject_text)
