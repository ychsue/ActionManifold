# src/am_core/decision_block.py

from __future__ import annotations
from typing import Any, Dict, Optional
from .playbook import Playbook


def decision_block(
    *,
    playbook: Playbook,
    current_state: str,
    enriched_output: Dict[str, Any],
) -> Optional[str]:
    """
    根據 enriched_output["status"] 決定下一個 state。

    語意：
    - 若 current_state 是 final → 回傳 None
    - 若 state_def 有 switch → 用 status 做字典 lookup
    - 若 state_def 有 to → 回傳 to
    - 若都沒有 → 回傳 None
    """

    # final state 不應該再 transition
    if playbook.is_final(current_state):
        return None

    state_def = playbook.get_state_def(current_state)

    # switch transition
    switch = state_def.get("switch")
    if switch:
        status = enriched_output.get("status")
        return switch.get(status)

    # linear transition
    if "to" in state_def:
        return state_def["to"]

    # 無法決定下一步
    return None