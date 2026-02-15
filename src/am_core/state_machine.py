# src/am_core/state_machine.py

from __future__ import annotations
from typing import Any, Dict, Optional

from .context import Ctx


class StateMachine:
    """
    語意：
    - StateMachine 是「原子」執行單元
    - 有 ctx（lexical scope）
    - 有 parent（通常是 Orchestrator 或 World）
    - 對外介面：async run(metadata) -> dict
    - 內部實作：_run(metadata) 由子類實作
    - emit(event) 會往 parent 冒泡（若 parent 有 emit）
    """

    def __init__(self, ctx: Ctx, parent: Optional[Any] = None) -> None:
        self.ctx = ctx
        self.parent = parent

    async def run(self, metadata: Dict[str, Any], mode: str = "normal") -> Dict[str, Any]:
        """
        對外統一協定：
        - 接受 metadata
        - 回傳 dict（至少應該有 status）
        - 可在過程中呼叫 self.emit(event)
        """
        if mode == "simulate":
            return await self._simulate(metadata)

        output = await self._run(metadata)
        return output

    async def _run(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        由子類實作的實際邏輯。
        預設丟錯，避免忘記覆寫。
        """
        raise NotImplementedError("StateMachine._run() must be implemented by subclasses")

    def emit(self, event: Dict[str, Any]) -> None:
        """
        將事件往 parent 冒泡。
        parent 可以是 Orchestrator / World / 其他具備 emit 的物件。
        """
        if self.parent and hasattr(self.parent, "emit"):
            self.parent.emit(event)
            
    async def _simulate(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        simulate 模式：不執行 _run()
        回傳預設或使用者提供的 output
        """
        rehearsal = self.ctx.get("rehearsal")
        state_name = self.ctx.get("current_state")

        override = rehearsal.decision_override.get(state_name, {})

        # 預設 output
        output = override.get("output", {"status": "ok"})

        return output
    
    