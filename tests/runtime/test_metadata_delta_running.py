# test_metadata_delta_running.py

import pytest
from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine
from am_core.ctx.ctx_wrapper import WrappedCtx, CtxDeltaCollector


class SetMetaSM(StateMachine):
    async def _run(self, wrapped_metadata):
        # 模擬 SM 修改 metadata
        wrapped_metadata.set("x", 42)
        return {"status": "ok"}

@pytest.mark.asyncio
async def test_metadata_delta_running():
    pb = Playbook({
        "states": [
            {"name": "A"},
        ],
        "registry": {
            "A": {"class_": SetMetaSM},
        },
        "initial": "A",
    })

    ctx = Ctx()
    orch = Orchestrator(pb, ctx)

    result = await orch.run()

    assert orch.metadata["x"] == 42