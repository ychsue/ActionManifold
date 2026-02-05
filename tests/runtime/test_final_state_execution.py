import pytest

from am_core.context import Ctx
from am_core.playbook import Playbook
from am_core.orchestrator import Orchestrator
from am_core.state_machine import StateMachine


class FinalState(StateMachine):
    async def _run(self, metadata):
        metadata["final_executed"] = True
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_final_state_is_executed_once():
    pb = Playbook({
        "initial": "FinalState",
        "final": ["FinalState"],
        "states": [
            {"name": "FinalState"}
        ],
        "registry": {
            "FinalState": FinalState
        }
    })

    ctx = Ctx()
    orch = Orchestrator(playbook=pb, ctx=ctx)

    result = await orch.run()

    assert result["final_state"] == "FinalState"
    assert result["metadata"]["final_executed"] is True