# tests/fake_runtime_store.py

from asyncio import Future
import asyncio
from typing import Dict, Any
from am_core.runtime_store import RuntimeStore

class FakeRuntimeStore(RuntimeStore):
    def __init__(self):
        self.active = {}
        self.pending = {}

    def register_orchestrator(self, orch):
        self.active[orch.orch_id] = orch

    def unregister_orchestrator(self, orch_id: str):
        self.active.pop(orch_id, None)

    def register_pending(self, orch_id: str, future: Future):
        # 這個future 只等待一秒
        loop = asyncio.get_event_loop()
        loop.call_later(0.1, lambda: future.set_result("FakeRuntimeStoreTimeout"))

        self.pending[orch_id] = future

    def unregister_pending(self, orch_id: str):
        self.pending.pop(orch_id, None)

    def resolve_pending(self, orch_id: str, decision):
        fut = self.pending.get(orch_id)
        if fut and not fut.done():
            fut.set_result(decision)

    def get_active_orchestrators(self):
        return dict(self.active)

    def get_pending(self):
        return dict(self.pending)
    
    def get_adapter_pending(self):
        return {}
    
    def register_adapter_pending(self, await_id: str, future) -> None:
        pass

    def resolve_adapter_pending(self, await_id: str, decision: Any) -> None:
        pass