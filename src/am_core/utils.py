import hashlib
import importlib
import importlib.machinery
import sys
import time
import types
from pathlib import Path
from typing import Any

def generate_event_id():
    return base36(int(time.time() * 1000))

def base36(num: int) -> str:
    """Convert an integer to a base36 string."""
    if num < 0:
        raise ValueError("Negative numbers are not supported.")
    if num == 0:
        return "0"

    digits = []
    while num:
        num, rem = divmod(num, 36)
        if rem < 10:
            digits.append(str(rem))
        else:
            digits.append(chr(rem - 10 + ord("a")))
    return "".join(reversed(digits))

def dynamic_import(path: str) -> Any:
    """
    Import a symbol from a 'module:attr' or 'module.attr' style path.

    Examples:
        "myproject.adapters.CLIAdapter"
        "myproject.adapters:CLIAdapter"
    """
    if ":" in path:
        module_name, attr = path.split(":", 1)
    else:
        parts = path.rsplit(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid import path: {path}")
        module_name, attr = parts

    module = importlib.import_module(module_name)
    try:
        return getattr(module, attr)
    except AttributeError as e:
        raise ImportError(f"Cannot import '{attr}' from '{module_name}'") from e


def dynamic_import_from_base_path(base_path: str, path: str) -> Any:
    """
    Import a symbol from a relative path anchored at a playbook directory.

    The generated module namespace is isolated per base_path so that multiple
    playbooks can each contain their own `states.*` modules without colliding.
    """
    if not path.startswith("."):
        raise ValueError(f"Relative import path must start with '.': {path}")

    module_path, _, attr = path[1:].rpartition(".")
    if not module_path or not attr:
        raise ValueError(f"Invalid relative import path: {path}")

    package_name = _ensure_dynamic_package(base_path)
    importlib.invalidate_caches()
    module = importlib.import_module(f"{package_name}.{module_path}")
    try:
        return getattr(module, attr)
    except AttributeError as e:
        raise ImportError(f"Cannot import '{attr}' from '{package_name}.{module_path}'") from e


def _ensure_dynamic_package(base_path: str) -> str:
    normalized_path = str(Path(base_path).resolve())
    digest = hashlib.sha1(normalized_path.encode("utf-8")).hexdigest()[:12]
    package_name = f"_am_pb_{digest}"

    if package_name in sys.modules:
        return package_name

    module = types.ModuleType(package_name)
    module.__file__ = normalized_path
    module.__package__ = package_name
    module.__path__ = [normalized_path]

    spec = importlib.machinery.ModuleSpec(package_name, loader=None, is_package=True)
    spec.submodule_search_locations = [normalized_path]
    module.__spec__ = spec

    sys.modules[package_name] = module
    return package_name
