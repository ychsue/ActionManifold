# tests/runtime/test_nested_orchestrator.py

import pytest

from am_core.context import Ctx
from am_core.playbook import Playbook
from am_core.orchestrator import Orchestrator
from am_core.state_machine import StateMachine


# ----------------------------------------
# 子流程的 StateMachine
# ----------------------------------------
class SubStart(StateMachine):
    async def _run(self, metadata):
        self.emit({"type": "sm",
                   "ctx_state": self.ctx.get("current_state"),
                   "parent_state": self.ctx.get("parent_state"),
                   "state": "SubStart"})
        return {"status": "ok"}


class SubEnd(StateMachine):
    async def _run(self, metadata):
        self.emit({"type": "sm",
                   "ctx_state": self.ctx.get("current_state"),
                   "parent_state": self.ctx.get("parent_state"),
                   "state": "SubEnd"})
        return {"status": "ok"}


# ----------------------------------------
# 主流程的 StateMachine
# ----------------------------------------
class MainStart(StateMachine):
    async def _run(self, metadata):
        self.emit({"type": "sm", "state": "MainStart"})
        return {"status": "ok"}


class MainEnd(StateMachine):
    async def _run(self, metadata):
        self.emit({"type": "sm", "state": "MainEnd"})
        return {"status": "ok"}


# ----------------------------------------
# 測試 nested orchestrator
# ----------------------------------------
@pytest.mark.asyncio
async def test_nested_orchestrator_execution(tmp_path):
    # -------------------------
    # 建立子流程 Playbook（subflow）
    # -------------------------
    sub_pb_data = {
        "initial": "SubStart",
        "final": ["SubEnd"],
        "states": [
            {"name": "SubStart", "to": "SubEnd"},
            {"name": "SubEnd"},
        ],
        "registry": {
            "SubStart": SubStart,
            "SubEnd": SubEnd,
        },
    }
    sub_pb = Playbook(sub_pb_data)

    # -------------------------
    # 建立主流程 Playbook（main flow）
    # -------------------------
    main_pb_data = {
        "initial": "MainStart",
        "final": ["MainEnd"],
        "states": [
            {"name": "MainStart", "to": "SubFlow"},
            {"name": "SubFlow", "to": "MainEnd"},  # nested orchestrator
            {"name": "MainEnd"},
        ],
        "registry": {
            "MainStart": MainStart,
            "MainEnd": MainEnd,
            # inline nested orchestrator
            "SubFlow": {
                "class": Orchestrator,
                "subflow": sub_pb,
            },
        },
    }
    main_pb = Playbook(main_pb_data)

    # -------------------------
    # 執行主 orchestrator
    # -------------------------
    root_state = "Root"
    ctx = Ctx(current_state=root_state)
    orch = Orchestrator(playbook=main_pb, ctx=ctx)

    result = await orch.run()

    # -------------------------
    # 驗證 final_state
    # -------------------------
    assert result["final_state"] == "MainEnd"

    # -------------------------
    # 驗證 event 冒泡（subflow → main）
    # -------------------------
    events = result["events"]
    states = [e["state"] for e in events]

    # 子流程事件
    assert "SubStart" in states
    assert "SubEnd" in states

    # 主流程事件
    assert "MainStart" in states
    assert "MainEnd" in states

    # -------------------------
    # 驗證 ctx 傳遞（lexical scope）
    # -------------------------
    # SubFlow 的 ctx 應該包含 current_state="SubFlow"
    # 但 MainStart / MainEnd 不應該有這個值
    subflow_ctx_values = [
        e.get("ctx_state")
        for e in events
        if e["state"] in ("SubStart", "SubEnd") and e.get("kind") is None
    ]
    subflow_ctx_values = [v for v in subflow_ctx_values if v is not None]

    assert subflow_ctx_values == ["SubStart", "SubEnd"]

    parent_ctx_values = [
        e.get("parent_state")
        for e in events
        if e["state"] in ("SubStart", "SubEnd")
    ]
    assert all(v == "SubFlow" for v in parent_ctx_values)
    
    assert all(e.get("parent_state") is root_state for e in events if e["state"] in ("MainStart", "MainEnd") and "parent_state" in e)