import ast
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_APP_ROOT = PROJECT_ROOT / "backend" / "app"


@dataclass(frozen=True)
class ImportReference:
    file_path: Path
    module: str
    line_number: int


def _python_files_under(relative_dir: str) -> list[Path]:
    scan_root = BACKEND_APP_ROOT / relative_dir
    if not scan_root.exists():
        return []
    return sorted(path for path in scan_root.rglob("*.py") if path.is_file())


def _module_name(path: Path) -> str:
    relative_path = path.relative_to(BACKEND_APP_ROOT.parent).with_suffix("")
    return ".".join(relative_path.parts)


def _iter_imports(path: Path) -> list[ImportReference]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imports: list[ImportReference] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(
                ImportReference(path, alias.name, node.lineno)
                for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_import_from(path, node)
            if module:
                imports.extend(
                    ImportReference(path, f"{module}.{alias.name}", node.lineno)
                    for alias in node.names
                )

    return imports


def _resolve_import_from(path: Path, node: ast.ImportFrom) -> str:
    if node.level == 0:
        return node.module or ""

    current_module_parts = _module_name(path).split(".")
    package_parts = current_module_parts[:-1]
    if node.level > len(package_parts):
        return node.module or ""

    base_parts = package_parts[: len(package_parts) - node.level + 1]
    if node.module:
        base_parts.extend(node.module.split("."))
    return ".".join(base_parts)


def _collect_violations(relative_dir: str, is_forbidden) -> list[ImportReference]:
    violations: list[ImportReference] = []
    for path in _python_files_under(relative_dir):
        violations.extend(
            import_ref
            for import_ref in _iter_imports(path)
            if is_forbidden(import_ref.module)
        )
    return violations


def _format_violations(violations: list[ImportReference]) -> str:
    details = [
        f"{violation.file_path.relative_to(PROJECT_ROOT)}:"
        f"{violation.line_number} 导入 {violation.module}"
        for violation in violations
    ]
    return "\n".join(details)


def _assert_no_forbidden_imports(
    relative_dir: str,
    is_forbidden,
    boundary_description: str,
) -> None:
    violations = _collect_violations(relative_dir, is_forbidden)

    assert not violations, (
        f"{boundary_description}，发现以下违规文件：\n"
        f"{_format_violations(violations)}"
    )


def test_services_layer_must_not_import_fastapi():
    """services 层不得依赖 FastAPI，HTTP 细节应停留在 API 层。"""
    _assert_no_forbidden_imports(
        "services",
        lambda module: module == "fastapi" or module.startswith("fastapi."),
        "services/* 不允许导入 FastAPI",
    )


def test_models_layer_must_not_import_logger():
    """models 层只表达数据结构与校验规则，不应直接依赖日志实现。"""
    _assert_no_forbidden_imports(
        "models",
        lambda module: module == "logger"
        or module.startswith("logger.")
        or module.endswith(".logger")
        or module.startswith("app.utils.logger.")
        or module.startswith("backend.app.utils.logger."),
        "models/* 不允许导入 logger",
    )


def test_core_layer_must_not_depend_on_api_layer():
    """core 层不得反向依赖 API 层，保持领域能力可被独立复用。"""
    _assert_no_forbidden_imports(
        "core",
        lambda module: module == "api"
        or module.startswith("api.")
        or module == "app.api"
        or module.startswith("app.api.")
        or module == "backend.app.api"
        or module.startswith("backend.app.api."),
        "core/* 不允许依赖 API 层",
    )
