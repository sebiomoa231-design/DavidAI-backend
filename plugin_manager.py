"""Plugin system (Section 19) -- discover, list, and execute plugins by name."""
from typing import Any, Callable, Dict

from david.utils.logger import get_logger

logger = get_logger("david.plugins")

_plugins: Dict[str, Callable[..., Any]] = {}


def register_plugin(name: str, fn: Callable[..., Any]) -> None:
    _plugins[name] = fn
    logger.info(f"plugin registered: {name}")


def list_plugins() -> list:
    return list(_plugins.keys())


def run_plugin(name: str, **kwargs) -> dict:
    if name not in _plugins:
        return {"success": False, "error": f"Plugin '{name}' not found"}
    try:
        result = _plugins[name](**kwargs)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"plugin '{name}' failed: {e}")
        return {"success": False, "error": str(e)}


def _autoload_builtins() -> None:
    from david.plugins.builtin import calculator, notes
    register_plugin("calculator", calculator.run)
    register_plugin("notes", notes.run)


_autoload_builtins()
