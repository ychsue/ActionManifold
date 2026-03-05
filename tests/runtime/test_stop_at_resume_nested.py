# tests/runtime/test_stop_at_resume_nested.py

import pytest
import asyncio

from streamlit import stop

from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator, Rehearsal
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine


def CountSMFactory(name):
    class _CountSM(StateMachine):
        async def _run(self, metadata):
            count = self.wrapped_ctx.get("count") or 0
            self.wrapped_ctx.set_nearest("count", count + 1)
            self.emit({"kind": "sm_executed", "state": name})
            return {"status": "ok"}
    return _CountSM


def subflow():
    return Playbook({
        "states": [
            {"name": "B1", "to": "B2"},
            {"name": "B2", "to": None},
        ],
        "initial": "B1",
        "registry": {
            "B1": CountSMFactory("B1"),
            "B2": CountSMFactory("B2"),
        }
    })


def rootflow():
    return Playbook({
        "states": [
            {"name": "A", "to": "Sub"},
            {"name": "Sub", "to": "Y"},
            {"name": "Y", "to": "Z"},
            {"name": "Z", "to": None},
        ],
        "initial": "A",
        "registry": {
            "A": CountSMFactory("A"),
            "Sub": {"class": Orchestrator, "subflow": subflow()},
            "Y": CountSMFactory("Y"),
            "Z": CountSMFactory("Z"),
        }
    })


@pytest.mark.asyncio
async def test_stop_at_resume_nested():
    # 第一次完整 run
    ctx = Ctx()
    orch = Orchestrator(rootflow(), ctx)
    await orch.run()
    event_log = ctx.get("rehearsal").event_log.copy()
    assert ctx.get("count") == 5  # A, B1, B2, Y, Z

    # 找到 B1 的 before_ini_child id
    b1_id = None
    for ev in event_log:
        if ev["kind"] == "before_ini_child" and ev["state"] == "B1":
            b1_id = ev["id"]
            break
    assert b1_id is not None
    
    # resume + stop_at="Y"
    stop_at = "Y"
    ctx2 = Ctx()
    ctx2.set("rehearsal", Rehearsal(
        mode="resume",
        event_log=event_log,
        resume_from_event_id=b1_id,
        stop_at=stop_at
    ))

    orch2 = Orchestrator(rootflow(), ctx2)
    result = await orch2.run()
    rehearsal = ctx2.get("rehearsal")
    last_event = rehearsal.event_log[-1]

    executed = [ev["state"] for ev in orch2.events if ev.get("kind") == "sm_executed"]

    # B1 mimic, B2 execute, Y execute but stop_at stops before running Z
    assert executed == ["B1","B2"]

    assert last_event["id"] == "stopped"
    assert last_event["state"] == stop_at
    assert ctx2.get("count") == 3