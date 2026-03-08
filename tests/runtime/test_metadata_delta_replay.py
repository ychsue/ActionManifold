# test_metadata_delta_replay.py

import pytest
from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator, Rehearsal
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine
from am_core.ctx.ctx_wrapper import WrappedCtx, CtxDeltaCollector


class SetMetaSM(StateMachine):
    async def _run(self, wrapped_metadata):
        wrapped_metadata.set("x", 99)
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_metadata_delta_replay():
    pb = Playbook({
        "states": [
            {"name": "A"},
        ],
        "registry": {
            "A": {"class": SetMetaSM},
        },
        "initial": "A",
    })

    # --- 第一次：normal run ---
    ctx1 = Ctx()
    orch1 = Orchestrator(pb, ctx1)
    await orch1.run()

    # event_log 裡應該有 metadata={"x":99}
    rehearsal: Rehearsal = ctx1.get("rehearsal")
    assert rehearsal is not None
    event_log = rehearsal.event_log
    after_ev = [ev for ev in event_log if ev["kind"] == "after_decision"][0]
    assert after_ev["metadata"]["x"] == 99

    # --- 第二次：replay ---
    ctx2 = Ctx()
    rehearsal.mode = "replay"  # set mode to replay
    ctx2.set("rehearsal", rehearsal)  # reuse event_log
    orch2 = Orchestrator(pb, ctx2)

    await orch2.run()

    # replay 時 metadata 必須 mimic event_log 裡的值
    assert orch2.metadata["x"] == 99