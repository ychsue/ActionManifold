# src/am_core/playbook.py

from typing import Any, Dict, List

from sympy import false


class Playbook:
    def __init__(self, spec: Dict[str, Any]):
        self._spec = spec
        self._states_index = {s["name"]: s for s in spec.get("states", [])}
        self._registry = spec.get("registry", {})

    # --- 基本語意 ---

    def initial_state(self) -> str:
        return self._spec["initial"]

    def is_final(self, state: str) -> bool:
        finals: List[str] = self._spec.get("final", [])
        return state in finals

    def get_state_def(self, state: str) -> Dict[str, Any]:
        try:
            return self._states_index[state]
        except KeyError:
            raise KeyError(f"State '{state}' not found in playbook.states")

    def get_state_class(self, state: str):
        try:
            return self._registry[state]
        except KeyError:
            raise KeyError(f"State class for '{state}' not found in playbook.registry")

    def instantiate_state(self, state: str, **kwargs):
        cls = self.get_state_class(state)
        return cls(**kwargs)

    # --- 專門給 decision_block / orchestrator 用的語意 ---

    def get_next_state_by_default_transition(self, stState: str, by_order = false) -> str | None:
        """
        對於只有 'to' 的簡單 state：
        { "name": "StartState", "to": "NextState" }
        若 沒有 'to'，且by_order is false則回傳 None
        若 沒有 'to'，且by_order is true則回傳 下一個 state name
        依照 playbook.states 的順序
        """
        state_def = self.get_state_def(stState)
        next_state = state_def.get("to")
        if next_state is None and by_order:
            states = self._spec.get("states", [])
            for i, s in enumerate(states):
                if s["name"] == stState and i + 1 < len(states):
                    next_state = states[i + 1]["name"]
                    break
        return next_state

    def get_switch_mapping(self, state: str) -> Dict[str, str] | None:
        """
        對於有 'switch' 的 state：
        { "name": "NextState", "switch": { "ok == True": "Success", ... } }
        """
        state_def = self.get_state_def(state)
        return state_def.get("switch")