# src/am_core/interactive/sse_adapter.py

import asyncio
import time
import uuid
from typing import Callable

from am_core.interactive.types import AwaitInput, InteractiveAdapter, ModifiedDecision
from am_core.runtime_store import RuntimeStore

class SSEAdapter(InteractiveAdapter):
    def __init__(self, runtime_store: RuntimeStore, emit: Callable[[dict], None]):
        self.runtime = runtime_store
        self.emit = emit  # 通常就是 world.emit

    async def handle(self, await_input: AwaitInput) -> ModifiedDecision:
        await_id = uuid.uuid4().hex
        loop = asyncio.get_event_loop()
        fut = loop.create_future()

        self.runtime.register_adapter_pending(await_id, fut)

        self.emit({
            "kind": "adapter_request",
            "await_id": await_id,
            "state": await_input["state"],
            "chain": await_input.get("chain"),
            "suggested": await_input["suggested"],
            "ui_hint": await_input.get("ui_hint", {}),
            "timestamp": time.time(),
        })

        decision = await fut  # 期待格式：{output, ctx_delta, metadata_delta}

        return ModifiedDecision(
            output=decision["output"],
            ctx_delta=decision["ctx_delta"],
            metadata_delta=decision["metadata_delta"],
        )
