import os
import inspect
import importlib
from typing import List
from .parser import parse_feature_unit
from .feature_unit import FeatureUnit


def file_to_module(root_path: str, file_path: str) -> str:
    """
    Convert a file path to a Python module path.
    Example:
      root_path = /project/am_project
      file_path = /project/am_project/flows/login.py
      → am_project.flows.login
    """
    rel = os.path.relpath(file_path, root_path)
    no_ext = os.path.splitext(rel)[0]
    parts = no_ext.split(os.sep)
    return ".".join(parts)


def collect_feature_units(root_path: str) -> List[FeatureUnit]:
    """
    Recursively scan root_path for .py files,
    import modules, and collect FeatureUnits.
    Only methods with @unit in docstring are collected.
    """
    units: List[FeatureUnit] = []

    for dirpath, _, filenames in os.walk(root_path):
        for fname in filenames:
            if not fname.endswith(".py"):
                continue

            file_path = os.path.join(dirpath, fname)
            module_path = file_to_module(root_path, file_path)

            try:
                module = importlib.import_module(module_path)
            except Exception:
                continue  # skip modules that fail to import

            # Scan classes
            for _, obj in inspect.getmembers(module, inspect.isclass):
                for _, method in inspect.getmembers(obj, inspect.isfunction):
                    fu = parse_feature_unit(method)
                    if fu:
                        units.append(fu)

            # Scan standalone functions
            for _, func in inspect.getmembers(module, inspect.isfunction):
                fu = parse_feature_unit(func)
                if fu:
                    units.append(fu)

    return units