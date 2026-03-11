# test_metadata_delta_resume.py

import pytest
from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine
from am_core.ctx.ctx_wrapper import WrappedCtx, CtxDeltaCollector


class SetMeta1(StateMachine):
    async def _run(self, wrapped_metadata):
        wrapped_metadata.set("x", 1)
        return {"status": "ok"}


class SetMeta2(StateMachine):
    async def _run(self, wrapped_metadata):
        wrapped_metadata.set("x", 2)
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_metadata_delta_resume():
    pb = Playbook({
        "registry": {
            "A": {"class_": SetMeta1, "next": "B"},
            "B": {"class_": SetMeta2},
        },
        "states": [
            {"name": "A", "to": "B"},
            {"name": "B", "to": None},
        ],
        "initial": "A"},
    )

    # --- 第一次：normal run ---
    ctx1 = Ctx()
    orch1 = Orchestrator(pb, ctx1)
    await orch1.run()

    # event_log 裡應該有兩次 metadata 設定
    rehearsal = ctx1.get("rehearsal")
    event_log = rehearsal.event_log
    ev_A = [ev for ev in event_log if ev["state"] == "A" and ev["kind"] == "after_decision"][0]
    ev_B = [ev for ev in event_log if ev["state"] == "B" and ev["kind"] == "after_decision"][0]

    assert ev_A["metadata"]["x"] == 1
    assert ev_B["metadata"]["x"] == 2

    # --- 第二次：resume 在 B 之前 ---
    rehearsal.mode = "resume"
    rehearsal.resume_from_event_id = ev_B["id"]

    ctx2 = Ctx()
    ctx2.set("rehearsal", rehearsal)
    orch2 = Orchestrator(pb, ctx2)

    await orch2.run()

    # resume 時：
    # - A 的 metadata 必須 mimic → x = 1
    # - B 的 metadata 必須重新執行 → x = 2
    assert orch2.metadata["x"] == 2