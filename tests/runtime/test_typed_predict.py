# tests/test_typed_predict.py
import pytest
from am_core.playbook import Playbook
from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator

from examples.example_sm_with_type import ExampleSM

@pytest.mark.asyncio
async def test_predict_and_run_apply():
    pb = Playbook({"initial": "A", "states": [{"name": "A", "class": "examples.example_sm_with_type.ExampleSM"}]})
    ctx = Ctx()
    orch = Orchestrator(pb, ctx)

    # preview: should apply predicted deltas (no side effects outside SM)
    await orch.run(sm_mode="preview")
    assert ctx.get("x") == 7
    assert orch.metadata.get("attempt") == 1

    # normal: run path should produce same output shape and apply deltas
    ctx2 = Ctx()
    orch2 = Orchestrator(pb, ctx2)
    await orch2.run(sm_mode="normal")
    assert ctx2.get("x") == 7
    assert orch2.metadata.get("attempt") == 1