# src/am_core/playbook.py

from __future__ import annotations
from inspect import isclass
from typing import Any, Dict, Optional
from pathlib import Path
import importlib
import json
import os

from am_core.state_machine import StateMachine

from .builtin_states import SuccessStateMachine, ErrorStateMachine, FailStateMachine

INTERNAL_STATES = {
    "Success": SuccessStateMachine,
    "Error": ErrorStateMachine,
    "Fail": FailStateMachine,
}

# PlaybookDict {
#     "initial": str,
#     "final": [str],
#     "states": [
#         {
#             "name": str,
#             "to": Optional[str],
#             "switch": Optional[dict[str,str]],
#             "timeout": Optional[number],
#             "retry_times": Optional[number],

#             # constructor info
#             "class": Optional[str],        # Python class path
#             "subflow": Optional[str|dict], # nested Playbook
#             "builtin": Optional[str],      # "Success", "Error", ...
#             "workdir": Optional[str],      # reserved for WORLD
#         }
#     ],
#     "registry": {
#         stateName: {
#             "class": Optional[type],       # Python class
#             "subflow": Optional[Playbook], # nested Playbook
#             "workdir": Optional[str],
#         }
#     }
# }

class Playbook:
    """
    Playbook 是一個可序列化的 Flow Graph + Resolver。
    不 import Orchestrator，不 instantiate Orchestrator。
    只回傳 constructor info，由 runtime 決定如何 instantiate。
    """

    def __init__(self, data: Dict[str, Any], base_path: Optional[str] = None):
        self.data = data
        self.base_path = base_path

        self.states = {s["name"]: s for s in data.get("states", [])}
        self.initial = data.get("initial")
        self.final = set(data.get("final", []))
        self.registry = data.get("registry", {})

    # -------------------------
    # 基本查詢
    # -------------------------
    def initial_state(self) -> str:
        if not self.initial:
            raise ValueError("Playbook has no initial state defined.")
        elif isinstance(self.initial, str):
            return self.initial
        else:
            raise ValueError(f"Playbook initial state must be a string. Got: {type(self.initial)}")
        
    def is_final(self, state: str) -> bool:
        return state in self.final

    def get_state_def(self, state: str) -> Dict[str, Any]:
        return self.states.get(state, {})

    # -------------------------
    # 解析 state constructor info
    # -------------------------
    def get_state_constructor(self, state: str) -> dict:
        """
        根據 schema（states + registry）組出 ctor_info：

        {
            "class": PythonClass,
            "subflow": Optional[Playbook],
            "workdir": Optional[str],
        }

        優先順序：
        1. states 裡的宣告（本地）
        2. registry 裡的宣告（外部注入）
        3. INTERNAL_STATES（內建 SM）
        """

        state_def = self.get_state_def(state)

        ctor: dict = {
            "class": None,
            "subflow": None,
            "workdir": None,
        }

        # -------------------------
        # 1. 先吃 registry（外部注入）
        # -------------------------
        if state in self.registry:
            entry = self.registry[state]
            if isclass(entry) and issubclass(entry, StateMachine):
                ctor["class"] = entry
            elif isinstance(entry, dict):
                ctor["class"] = entry.get("class") or ctor["class"]
                ctor["subflow"] = entry.get("subflow") or ctor["subflow"]
                ctor["workdir"] = entry.get("workdir") or ctor["workdir"]

        # -------------------------
        # 2. 再吃 states（本地宣告，覆寫 registry）
        # -------------------------

        # 2-1 builtin：內建 SM（Success / Error / Fail）
        builtin_name = state_def.get("builtin")
        if builtin_name:
            if builtin_name not in INTERNAL_STATES:
                raise ValueError(f"Unknown builtin state: {builtin_name}")
            ctor["class"] = INTERNAL_STATES[builtin_name]

        # 2-2 class：Python class path（"a.b.C"）
        class_path = state_def.get("class")
        if class_path:
            module_name, _, cls_name = class_path.rpartition(".")
            if not module_name or not cls_name:
                raise ValueError(f"Invalid class path for state {state}: {class_path}")
            module = importlib.import_module(module_name)
            ctor["class"] = getattr(module, cls_name)

        # 2-3 subflow：巢狀 Playbook（dict 或 "playbook:xxx.json"）
        subflow = state_def.get("subflow")
        if subflow is not None:
            if isinstance(subflow, dict):
                ctor["subflow"] = Playbook(subflow, base_path=self.base_path)
            elif isinstance(subflow, str):
                if subflow.startswith("playbook:"):
                    rel_path = subflow.split(":", 1)[1]
                    pb_path = Path(self.base_path or ".") / rel_path
                    with pb_path.open("r", encoding="utf-8") as f:
                        pb_data = json.load(f)
                    ctor["subflow"] = Playbook(pb_data, base_path=str(pb_path.parent))
                else:
                    raise ValueError(f"Unsupported subflow string for state {state}: {subflow}")
            else:
                raise TypeError(f"Invalid subflow type for state {state}: {type(subflow)}")

        # 2-4 workdir：目前先只是 pass-through，未來給 WORLD 用
        if "workdir" in state_def:
            ctor["workdir"] = state_def["workdir"]

        # -------------------------
        # 3. 若什麼都沒有，試試 INTERNAL_STATES（state 名稱本身）
        # -------------------------
        if ctor["class"] is None and state in INTERNAL_STATES:
            ctor["class"] = INTERNAL_STATES[state]
            
        if ctor["class"] is None and ctor["subflow"] is not None:
            from .orchestrator import Orchestrator  # 避免循環 import
            ctor["class"] = Orchestrator  # 若有 subflow 卻沒指定 class，預設用 Orchestrator

        if ctor["class"] is None:
            raise ValueError(f"No constructor found for state {state}")

        return ctor
    # -------------------------
    # type resolver
    # -------------------------
    def _resolve_type(self, type_str: str) -> Dict[str, Any]:

        if type_str.startswith("python:"):
            cls = self._load_python_class(type_str[len("python:"):])
            return {"kind": "python", "class": cls}

        if type_str.startswith("playbook:"):
            pb = self._load_sub_playbook(type_str[len("playbook:"):])
            return {"kind": "orchestrator", "playbook": pb}

        if type_str.startswith("world:"):
            return self._load_world(type_str[len("world:"):])

        raise ValueError(f"Unknown type: {type_str}")

    # -------------------------
    # python class loader
    # -------------------------
    def _load_python_class(self, path: str):
        module_name, class_name = path.rsplit(".", 1)
        module = importlib.import_module(module_name)
        return getattr(module, class_name)

    # -------------------------
    # nested playbook loader
    # -------------------------
    def _load_sub_playbook(self, path: str):
        full_path = self._resolve_path(path)
        with open(full_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return Playbook(data, base_path=os.path.dirname(full_path))

    # -------------------------
    # world loader（未來可擴充）
    # -------------------------
    def _load_world(self, path: str):
        full_path = self._resolve_path(path)
        with open(full_path, "r", encoding="utf-8") as f:
            world_cfg = json.load(f)

        sub_pb = Playbook(world_cfg["playbook"], base_path=os.path.dirname(full_path))

        return {
            "kind": "world",
            "playbook": sub_pb,
            "workdir": world_cfg.get("workdir"),
        }

    # -------------------------
    # path resolver
    # -------------------------
    def _resolve_path(self, path: str) -> str:
        if self.base_path:
            return os.path.join(self.base_path, path)
        return path