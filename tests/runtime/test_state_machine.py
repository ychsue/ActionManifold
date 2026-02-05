# tests/runtime/test_state_machine.py

import asyncio
import pytest

from am_core.context import Ctx
from am_core.state_machine import StateMachine


class DummyParent:
    def __init__(self):
        self.events = []

    def emit(self, event):
        self.events.append(event)


class EchoState(StateMachine):
    async def _run(self, metadata):
        self.emit({"type": "echo", "meta": metadata})
        return {"status": "ok", "echo": metadata}

@pytest.mark.asyncio
async def test_state_machine_emit_and_run():
    ctx = Ctx()
    parent = DummyParent()
    sm = EchoState(ctx=ctx, parent=parent)

    metadata = {"x": 1}
    output = await sm.run(metadata)

    assert output["status"] == "ok"
    assert output["echo"] == metadata

    assert len(parent.events) == 1
    assert parent.events[0]["type"] == "echo"
    assert parent.events[0]["meta"] == metadata