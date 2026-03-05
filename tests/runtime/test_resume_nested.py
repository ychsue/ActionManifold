import pytest
import asyncio

from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator, Rehearsal
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine


# --- 測試用 SM：每次執行會把 ctx["count"] += 1 ---
def CountSMFactory(name):
    class _CountSM(StateMachine):
        def __init__(self, wrapped_ctx, parent, name):
            super().__init__(wrapped_ctx, parent, name)
            self.name = name

        async def _run(self, metadata):
            count = self.wrapped_ctx.get("count") or 0
            self.wrapped_ctx.set_nearest("count", count + 1)

            # emit event for replay/resume test
            self.emit({
                "kind": "sm_executed",
                "state": self.name,
            })

            return {"status": "ok"}

    _CountSM.__name__ = f"CountSM_{name}"
    return _CountSM

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
                "B1": CountSMFactory("B1"),
                "B2": CountSMFactory("B2"),
            },
        }
    )


# --- Root flow：A → Sub → Z ---
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
                "A": CountSMFactory("A"),
                "Sub": {
                    "class": Orchestrator,
                    "subflow": subflow_playbook(),
                },
                "Z": CountSMFactory("Z"),
            },
        }
    )


@pytest.mark.asyncio
async def test_resume_nested():
    # --- 第一次 run：產生 event_log ---
    ctx = Ctx()
    pb = root_playbook()
    orch = Orchestrator(pb, ctx)

    result1 = await orch.run()
    event_log = ctx.get("rehearsal").event_log.copy()

    # A(1) + B1(1) + B2(1) + Z(1) = 4
    assert result1["final_state"] == "Z"
    assert ctx.get("count") == 4

    # 找到 B1 的 after_decision event_id
    b1_after = None
    for ev in event_log:
        if ev["kind"] == "after_decision" and ev["state"] == "B1":
            b1_after = ev["id"]
            break
    assert b1_after is not None

    # --- 第二次 run：resume 模式 ---
    ctx2 = Ctx()
    ctx2.set(
        "rehearsal",
        Rehearsal(
            mode="resume",
            event_log=event_log,
            resume_from_event_id=b1_after,
        ),
    )

    orch2 = Orchestrator(pb, ctx2)
    result2 = await orch2.run()

    executed = [ev["state"] for ev in orch2.events if ev.get("kind") == "sm_executed"]
    assert executed == ["B1", "B2", "Z"]

    # resume 後 final_state 應該一樣
    assert result2["final_state"] == "Z"

    # resume 後 count = 4 + B2(1) + Z(1) = 4
    assert ctx2.get("count") == 4