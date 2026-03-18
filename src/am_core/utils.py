import time
import importlib
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
