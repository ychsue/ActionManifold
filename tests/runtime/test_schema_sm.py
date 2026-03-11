# tests/test_schema_sm.py

import pytest
from typing_extensions import NotRequired
from typing import Any, TypedDict

from am_core.ctx.metadata_wrapper import WrappedMetadata
from am_core.state_machine import StateMachine
from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator
from am_core.playbook import Playbook


class MyOutputSchema(TypedDict):
    status: str
    value: NotRequired[int]


class SchemaSM(StateMachine[MyOutputSchema,Any,Any]):
    async def predict_output(self) -> MyOutputSchema:
        return {"status": "ok", "value": 42}

    async def predict_ctx_delta(self):
        return []

    async def predict_metadata_delta(self):
        return {}

    async def _run(self, wrapped_metadata: WrappedMetadata) -> MyOutputSchema:
        # 真實執行：回傳與 predict_output 一致的 schema
        return {"status": "ok", "value": 42}


@pytest.mark.asyncio
async def test_schema_sm_preview_and_normal():
    pb = Playbook(
        data={
            "initial": "A",
            "states": [
                {"name": "A", "class_": "tests.runtime.test_schema_sm.SchemaSM"},
            ],
        }
    )

    ctx = Ctx()
    orch = Orchestrator(pb, ctx)

    # preview
    result_preview = await orch.run(sm_mode="preview")
    assert result_preview["final_state"] == "A"
    assert orch.metadata == {'retries': {}} # run_watcher 自動添加的 metadata

    # normal
    ctx2 = Ctx()
    orch2 = Orchestrator(pb, ctx2)
    result_normal = await orch2.run(sm_mode="normal")
    assert result_normal["final_state"] == "A"
    assert orch2.metadata == {'retries': {}}  # run_watcher 自動添加的 metadata