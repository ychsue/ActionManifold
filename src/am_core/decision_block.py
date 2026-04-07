# src/am_core/decision_block.py

from typing import Any, Dict, Optional
from .playbook import Playbook


def decision_block(playbook: Playbook, current_state: str, enriched_output: Dict[str, Any]) -> Optional[str]:
    """
    根據 enriched_output 決定下一個 state。
   - 若 state_def 有 switch → 用 status 做字典 lookup
    - 若 state_def 有 to → 回傳 to
    - 若都沒有 → 回傳 None
    """
    state_def = playbook.get_state_def(current_state)
    sm_status = enriched_output["status"]
    if state_def is None:
        raise ValueError(f"State {current_state} not found in playbook states")
    # 1. switch 語意
    if "switch" in state_def:
        sw = state_def["switch"]
        if sm_status in sw:
            return sw[sm_status]
        elif sm_status == "fail":
            return "Fail"  # 預設 fail 就轉 Fail 狀態
        
        # 若沒有對應，則要顯示錯誤
        raise ValueError(f"State {current_state} has switch but no case for status '{sm_status}'")

    # 2. to 語意
    if "to" in state_def:
        return state_def["to"]

    # 3. fallback：依 states 順序
    states = list(playbook.states.keys())
    if current_state in states:
        idx = states.index(current_state)
        if idx + 1 < len(states):
            return states[idx + 1]

    # 4. 沒有下一步 → 結束
    return None