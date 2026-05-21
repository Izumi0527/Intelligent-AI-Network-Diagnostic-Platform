from pathlib import Path
import re


def test_backend_package_readme_metadata_is_resolvable():
    """后端包元数据声明的 readme 必须能被 hatchling 构建后端解析。"""
    project_root = Path(__file__).resolve().parents[1]
    pyproject_path = project_root / "backend" / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8")

    project_section = re.search(
        r"(?ms)^\[project\]\s*(.*?)(?=^\[|\Z)",
        pyproject_text,
    )
    assert project_section is not None

    readme = re.search(r'(?m)^readme\s*=\s*"([^"]+)"\s*$', project_section.group(1))
    assert readme is not None
    assert (pyproject_path.parent / readme.group(1)).resolve().is_file()
