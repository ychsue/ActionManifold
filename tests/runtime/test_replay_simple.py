from atexit import register
import pytest
import asyncio

from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator, Rehearsal
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine


# --- 測試用 SM：每次執行會把 ctx["count"] += 1 ---
class CountSM(StateMachine):
    # async def _run(self, metadata):
    #     parent = self.ctx._parent
    #     if parent is None:
    #         raise ValueError("CountSM requires a parent context to store count")
    #     count = parent.get("count") or 0
    #     parent.set("count", count + 1)
    #     return {"status": "ok"}
    async def _run(self, metadata):
        count = self.wrapped_ctx.get("count") or 0
        self.wrapped_ctx.set_nearest("count", count + 1)
        return {"status": "ok"}

# --- 建立簡單 playbook：A → B → C ---
def simple_playbook():
    return Playbook(
        {"states":[
            {"name": "A", "to": "B"},
            {"name": "B", "to": "C"},
            {"name": "C", "to": None},
        ],
        "initial":"A",
        "registry":{
            "A":CountSM,
            "B": CountSM,
            "C": CountSM,            
        }}
    )


@pytest.mark.asyncio
async def test_replay_simple():
    # --- 第一次 run：產生 event_log ---
    ctx = Ctx()
    pb = simple_playbook()
    orch = Orchestrator(pb, ctx)

    result1 = await orch.run()
    event_log = ctx.get("rehearsal").event_log.copy()

    # 驗證第一次 run 的結果
    assert result1["final_state"] == "C"
    assert ctx.get("count") == 3

    # --- 第二次 run：replay 模式 ---
    ctx2 = Ctx()
    ctx2.set("rehearsal", Rehearsal(mode="replay", event_log=event_log))

    orch2 = Orchestrator(pb, ctx2)

    result2 = await orch2.run()

    # 驗證 replay 的結果與第一次一致
    assert result2["final_state"] == "C"
    assert ctx2.get("count") == 3

    # 驗證 replay 不會執行 child.run（count 不會再增加）
    assert ctx2.get("count") == ctx.get("count")