# tests/runtime/test_stop_at_normal.py

import pytest
import asyncio

from am_core.context import Ctx
from am_core.orchestrator import Orchestrator, Rehearsal
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine


def CountSMFactory(name):
    class _CountSM(StateMachine):
        async def _run(self, metadata):
            count = self.ctx.get("count") or 0
            self.ctx.set_nearest("count", count + 1)
            self.emit({"kind": "sm_executed", "state": name})
            return {"status": "ok"}
    return _CountSM


def simple_playbook():
    return Playbook({
        "states": [
            {"name": "A", "to": "B"},
            {"name": "B", "to": "C"},
            {"name": "C", "to": "D"},
            {"name": "D", "to": None},
        ],
        "initial": "A",
        "registry": {
            "A": CountSMFactory("A"),
            "B": CountSMFactory("B"),
            "C": CountSMFactory("C"),
            "D": CountSMFactory("D"),
        }
    })


@pytest.mark.asyncio
async def test_stop_at_normal():
    ctx = Ctx()
    ctx.set("rehearsal", Rehearsal(mode="normal", stop_at="C"))

    orch = Orchestrator(simple_playbook(), ctx)
    result = await orch.run()

    executed = [ev["state"] for ev in orch.events if ev.get("kind") == "sm_executed"]

    assert executed == ["A", "B"]
    assert result["final_state"] == "C"
    assert ctx.get("count") == 2