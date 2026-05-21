"""后端目录启动时的 Python 字节码写入策略。"""

import sys

sys.dont_write_bytecode = True

from pathlib import Path


def _remove_sitecustomize_cache() -> None:
    """清理 sitecustomize 自身导入时可能产生的字节码缓存。"""
    cache_dir = Path(__file__).with_name("__pycache__")
    if not cache_dir.exists():
        return

    for cache_file in cache_dir.glob("sitecustomize*.py[co]"):
        cache_file.unlink(missing_ok=True)

    try:
        cache_dir.rmdir()
    except OSError:
        pass


_remove_sitecustomize_cache()


def _remove_virtualenv_startup_cache() -> None:
    """清理 virtualenv 启动钩子早于本文件产生的字节码缓存。"""
    for entry in sys.path:
        if not entry:
            continue

        path = Path(entry)
        if path.name != "site-packages":
            continue

        cache_dir = path / "__pycache__"
        if not cache_dir.exists():
            continue

        for cache_file in cache_dir.glob("_virtualenv*.py[co]"):
            try:
                cache_file.unlink(missing_ok=True)
            except OSError:
                pass

        try:
            cache_dir.rmdir()
        except OSError:
            pass


_remove_virtualenv_startup_cache()
