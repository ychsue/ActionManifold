from .ctx.context import Ctx
from typing import Any, Optional

class RefGuard:
    """
    RefGuard 的 使用方式
    ``` py
    from am_core.ref_guard import RefGuard
    from am_core.event_guard import EventGuard

    class LoginFlow(Orchestrator):
        async def run(self, auto_sequence=True):
            # 只有需要事件監聽的 orchestrator 才需要這段
            async with EventGuard("win_event", self._on_event) as fg:
                async with RefGuard(self.orchCtx, "foreground_guard", fg):
                    return await super().run(auto_sequence)

        def _on_event(self, event):
            # 處理事件
            ...
    ```
    """
    def __init__(self, ctx: Ctx, key: str, value: Any):
        self.ctx = ctx
        self.key = key
        self.value = value
        self.had_local = False
        self.old_value = None

    async def __aenter__(self):
        if self.key in self.ctx.ref:
            self.had_local = True
            self.old_value = self.ctx.ref[self.key]
        self.ctx.ref[self.key] = self.value
        return self.value

    async def __aexit__(self, exc_type, exc, tb):
        if self.had_local:
            self.ctx.ref[self.key] = self.old_value
        else:
            self.ctx.ref.pop(self.key, None)