import pytest

from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine
from am_core.interactive.adapters.fake_adapter import FakeAdapter
from am_core.interactive.types import AwaitInput, ModifiedDecision


class InteractiveSM(StateMachine):
    async def predict_output(self):
        return {"status": "ok", "value": 1}

    async def predict_ctx_delta(self):
        return [{"mode": "root", "key": "x", "to": 1}]

    async def predict_metadata_delta(self):
        return {"m": 1}

    async def _run(self, wrapped_metadata):
        return {"status": "ok", "value": 1}


@pytest.mark.asyncio
async def test_interactive_simulate_with_fake_adapter(monkeypatch):
    pb = Playbook({
        "initial": "A",
        "states": [
            {"name": "A", "class_": "tests.runtime.test_interactive_with_adapter.InteractiveSM"},
            {"name": "B", "builtin": "Success"},
        ],
    })

    ctx = Ctx()
    # 在 root ctx 設定 adapter class 路徑（string）
    ctx.set("interactive_adapter", "am_core.interactive.adapters.fake_adapter.FakeAdapter")

    orch = Orchestrator(pb, ctx)

    # monkeypatch dynamic_import 讓它回傳 FakeAdapter class
    from am_core import utils as imports_mod
    from am_core.interactive.adapters.fake_adapter import FakeAdapter as FA

    # Step 1: 建立 FakeAdapter instance（含 patch）
    adapter = FakeAdapter(
        output_patch={"A": {"value": 42}},
        ctx_delta_patch={"A": [{"mode": "root", "key": "x", "to": 42}]},
        metadata_patch={"A": {"m": 42}},
    )

    # Step 2: 把 instance 塞進 ctx（測試專用）
    ctx.set_interactive_adapter(adapter)

    orch = Orchestrator(pb, ctx)

    # Step 3: run interactive_simulate
    result = await orch.run(sm_mode="interactive_simulate")

    # Step 4: 驗證 patch 已被 apply
    assert ctx.get("x") == 42
    assert orch.metadata.get("m") == 42

    # Step 5: 驗證下一 state 正常執行
    assert result["final_state"] == "B"
