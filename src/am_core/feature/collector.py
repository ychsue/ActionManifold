import sys
import inspect
import importlib.util
import pkgutil
from pathlib import Path
from typing import List

from git import Optional
from .feature_unit import FEATURE_UNITS, feature_unit

@feature_unit(
    belongs_to=["DevEngine"],
    status="done",
    display_name="Collect Feature Units",
    notes="遞迴掃描 root_path，收集所有帶有 @unit 的方法並轉為 FeatureUnit"
)
def collect_feature_units(root_path: str, pkg_path: Optional[str] = None) -> List:
    """
    root_path: 字串路徑，例如 "src" 或 "am_meta"
    pkg_path: package 根目錄路徑，用於決定 module 名稱，預設為 root_path
    掃描該路徑下所有 .py 檔案，import 它們，並收集 FeatureUnit。
    """

    root = Path(root_path).resolve()

    if not root.exists():
        raise ValueError(f"Root path does not exist: {root}")

    if pkg_path is None:
        pkg_dir = root
    else:
        pkg_dir = Path(pkg_path).resolve()
        
    # 將 pkg_dir 加入 sys.path，確保可以 import
    if str(pkg_dir) not in sys.path:
        sys.path.insert(0, str(pkg_dir))

    for py_file in root.rglob("*.py"):
        module_name = _module_name_from_path(pkg_dir, py_file)

        if module_name in sys.modules:
            continue

        spec = importlib.util.spec_from_file_location(module_name, py_file)
        if spec is None or spec.loader is None:
            print(f"[collector] Could not load spec for {module_name}")
            continue
        module = importlib.util.module_from_spec(spec)

        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            print(f"[collector] Failed to import {module_name}: {e}")

    return list(FEATURE_UNITS.values())


def _module_name_from_path(root: Path, file: Path) -> str:
    rel = file.relative_to(root)
    parts = rel.with_suffix("").parts
    return ".".join(parts)

def collect_feature_units_by_package(package) -> List:
    """
    掃描整個 package，import 所有 modules，
    並從 FEATURE_UNITS registry 收集所有 FeatureUnit。
    """

    package_path = Path(package.__file__).parent

    for module_info in pkgutil.walk_packages([str(package_path)], package.__name__ + "."):
        module_name = module_info.name

        # 避免重複 import
        if module_name in globals().get("_imported_modules", set()):
            continue

        globals().setdefault("_imported_modules", set()).add(module_name)

        try:
            importlib.import_module(module_name)
        except Exception as e:
            print(f"[collector] Failed to import {module_name}: {e}")

    # registry 已經是 symbol-based，不會重複
    return list(FEATURE_UNITS.values())