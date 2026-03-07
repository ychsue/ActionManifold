import pytest
import asyncio

from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator, Rehearsal
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine


# --- 測試用 SM：每次執行會把 ctx["count"] += 1 ---
class CountSM(StateMachine):
    async def _run(self, wrapped_metadata):
        count = self.wrapped_ctx.get("count") or 0
        # 用 nearest，讓 count 寫在「最接近有 count 的 ctx」上
        self.wrapped_ctx.set_nearest("count", count + 1)
        return {"status": "ok"}


# --- Subflow：B1 → B2 ---
def subflow_playbook():
    return Playbook(
        {
            "states": [
                {"name": "B1", "to": "B2"},
                {"name": "B2", "to": None},
            ],
            "initial": "B1",
            "registry": {
                "B1": CountSM,
                "B2": CountSM,
            },
        }
    )


# --- Root flow：A → SubOrch → Z ---
def root_playbook():
    return Playbook(
        {
            "states": [
                {"name": "A", "to": "Sub"},
                {"name": "Sub", "to": "Z"},
                {"name": "Z", "to": None},
            ],
            "initial": "A",
            "registry": {
                "A": CountSM,
                # 這裡用 Orchestrator 當作子流程
                "Sub": {
                    "class": Orchestrator,
                    "subflow": subflow_playbook(),                    
                    },
                "Z": CountSM,
            },
        }
    )


@pytest.mark.asyncio
async def test_replay_nested():
    # --- 第一次 run：產生 event_log ---
    ctx = Ctx()
    pb = root_playbook()
    orch = Orchestrator(pb, ctx)

    result1 = await orch.run()
    event_log = ctx.get("rehearsal").event_log.copy()

    # A(1) + B1(1) + B2(1) + Z(1) = 4
    assert result1["final_state"] == "Z"
    assert ctx.get("count") == 4

    # --- 第二次 run：replay 模式 ---
    ctx2 = Ctx()
    ctx2.set("rehearsal", Rehearsal(mode="replay", event_log=event_log))

    orch2 = Orchestrator(pb, ctx2)
    result2 = await orch2.run()

    # replay 後 final_state 應該一樣
    assert result2["final_state"] == "Z"

    # replay 應該只 mimic，不重新執行 SM：count 仍然是 4
    assert ctx2.get("count") == 4
    assert ctx2.get("count") == ctx.get("count")
    
@pytest.mark.asyncio
async def test_replay_nested_state_level():
    # --- 第一次 run：產生 event_log ---
    ctx = Ctx()
    pb = root_playbook()
    orch = Orchestrator(pb, ctx)

    result1 = await orch.run()
    event_log = ctx.get("rehearsal").event_log.copy()

    # A(1) + B1(1) + B2(1) + Z(1) = 4
    assert result1["final_state"] == "Z"
    assert ctx.get("count") == 4

    # --- 第二次 run：replay 模式（level="state"） ---
    ctx2 = Ctx()
    ctx2.set(
        "rehearsal",
        Rehearsal(
            mode="replay",
            level="state",   # <── 這行讓 replay 會跑進 Sub
            event_log=event_log,
        ),
    )

    orch2 = Orchestrator(pb, ctx2)
    result2 = await orch2.run()

    # replay 後 final_state 應該一樣
    assert result2["final_state"] == "Z"

    # replay 應該只 mimic，不重新執行 SM：count 仍然是 4
    assert ctx2.get("count") == 4
    assert ctx2.get("count") == ctx.get("count")
