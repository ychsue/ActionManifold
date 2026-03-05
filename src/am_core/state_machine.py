# src/am_core/state_machine.py

from __future__ import annotations
from typing import Any, Dict, Optional

from am_core.ctx.ctx_wrapper import CtxDeltaCollector, WrappedCtx

from .ctx.context import Ctx


class StateMachine:
    def __init__(self, wrapped_ctx: WrappedCtx, parent: Optional[Any] = None, name: Optional[str] = None):
        self.wrapped_ctx = wrapped_ctx
        self.parent = parent
        self.name = name
        self._metadata_delta = {}

    async def run(self, metadata, mode="normal"):
        wrapped_ctx = self.wrapped_ctx

        if mode == "normal":
            output = await self._run(metadata)
        elif mode == "preview":
            output = await self._preview(metadata)
        elif mode == "interactive_simulate":
            output = await self._interactive_simulate(metadata)
        else:
            raise ValueError(f"Unknown mode: {mode}")

        return {
            "status": output.get("status", "ok"),
            "is_SM": True,
            "output": output,
            "ctx_delta": list(wrapped_ctx._delta.ops),  # 轉成一般 list，方便序列化
            "metadata_delta": dict(self._metadata_delta),
        }

    def emit(self, event: Dict[str, Any]) -> None:
        """
        將事件往 parent 冒泡。
        parent 可以是 Orchestrator / World / 其他具備 emit 的物件。
        """
        if self.parent and hasattr(self.parent, "emit"):
            self.parent.emit(event)

    # --- 三種策略：子類別可以覆寫這三個 ---

    async def _run(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        真實執行：有 side effect、有真實 ctx_delta / metadata_delta
        """
        raise NotImplementedError

    async def _preview(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        預演：無 side effect，但要產生「模擬的」 output / ctx_delta / metadata_delta
        預設行為：直接呼叫 _run（子類別可以覆寫成純計算版）
        """
        return await self._run(metadata)

    async def _interactive_simulate(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        互動模擬：無 side effect，但會停下來讓使用者調整 ctx_delta / metadata_delta
        預設行為：先用 _preview 拿預設值，再給上層（UI）決定怎麼問人
        """
        preview_output = await self._preview(metadata)
        # 這裡先保留 hook，之後我們再決定怎麼跟 UI 對話
        return preview_output