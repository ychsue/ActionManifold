# tests/runtime/test_stop_at_replay.py

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
async def test_stop_at_replay():
    # 第一次正常跑完
    ctx = Ctx()
    orch = Orchestrator(simple_playbook(), ctx)
    await orch.run()
    event_log = ctx.get("rehearsal").event_log.copy()
    assert ctx.get("count") == 4

    # 第二次 replay
    ctx2 = Ctx()
    ctx2.set("rehearsal", Rehearsal(mode="replay", event_log=event_log, stop_at="C"))

    orch2 = Orchestrator(simple_playbook(), ctx2)
    result = await orch2.run()

    executed = [ev["state"] for ev in orch2.events if ev.get("kind") == "sm_executed"]

    assert executed == []  # replay 不執行 SM
    assert result["final_state"] == "C"
    assert ctx2.get("count") is None or ctx2.get("count") == 2