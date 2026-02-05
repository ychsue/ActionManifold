# src/am_core/playbook.py

from __future__ import annotations
from typing import Any, Dict, Optional
import importlib
import json
import os

from .builtin_states import SuccessStateMachine, ErrorStateMachine, FailStateMachine

INTERNAL_STATES = {
    "Success": SuccessStateMachine,
    "Error": ErrorStateMachine,
    "Fail": FailStateMachine,
}

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
    def get_state_constructor(self, state: str) -> Dict[str, Any]:
        """
        回傳 constructor info：
        {
            "kind": "python" | "orchestrator" | "world",
            "class": <python class> (optional),
            "playbook": <Playbook> (optional),
            "path": <file path> (optional)
        }
        """
        # 0. internal builtin states
        if state in INTERNAL_STATES:
            return {
                "kind": "python",
                "class": INTERNAL_STATES[state],
            }
        
        state_def = self.get_state_def(state)

        # 1. inline class
        if state in self.registry and isinstance(self.registry[state], type):
            return {
                "kind": "python",
                "class": self.registry[state],
            }

        # 2. inline nested orchestrator
        if state in self.registry and isinstance(self.registry[state], dict):
            entry = self.registry[state]
            playbook = entry.get("playbook")
            playbook = Playbook(playbook, base_path=self.base_path) if isinstance(playbook, dict) else playbook
            return {
                "kind": "orchestrator",
                "class": entry.get("cls", None),
                "playbook": entry["playbook"],
            }

        # 3. type resolver
        if "type" in state_def:
            return self._resolve_type(state_def["type"])

        raise ValueError(f"Cannot resolve constructor for state: {state}")

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