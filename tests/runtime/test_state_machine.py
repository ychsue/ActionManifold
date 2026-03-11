# tests/runtime/test_state_machine.py

import asyncio
from typing import Any, Dict
import pytest

from am_core.ctx.context import Ctx
from am_core.ctx.ctx_wrapper import CtxDeltaCollector, WrappedCtx
from am_core.ctx.metadata_wrapper import WrappedMetadata
from am_core.state_machine import StateMachine


class DummyParent:
    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)


class EchoState(StateMachine):
    async def _run(self, wrapped_metadata: WrappedMetadata):
        self.emit({"type": "echo", "meta": wrapped_metadata._real})
        return {"status": "ok", "echo": wrapped_metadata._real}
    
    async def predict_output(self) -> Dict[str, Any]:
        output = (await super().predict_output())
        output["echo"] = 1
        return output

@pytest.mark.asyncio
async def test_state_machine_emit_and_run():
    ctx = Ctx()
    wrapped_ctx = WrappedCtx(ctx, CtxDeltaCollector())
    parent = DummyParent()
    sm = EchoState(wrapped_ctx=wrapped_ctx, parent=parent, name="EchoState")

    metadata = {"x": 1}
    output = await sm.run(metadata)
    sm_output = output["output"]

    assert output["status"] == "ok"
    assert sm_output["echo"] == metadata

    assert len(parent.events) == 1
    assert parent.events[0]["type"] == "echo"
    assert parent.events[0]["meta"] == metadata