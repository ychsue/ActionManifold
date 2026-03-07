import pytest

from am_core.ctx.context import Ctx
from am_core.playbook import Playbook
from am_core.orchestrator import Orchestrator
from am_core.state_machine import StateMachine


class A(StateMachine):
    async def _run(self, wrapped_metadata):
        wrapped_metadata.set("order", ["A"])
        return {"status": "ok"}


class B(StateMachine):
    async def _run(self, wrapped_metadata):
        orders = wrapped_metadata.get("order") or []
        orders.append("B")
        wrapped_metadata.set("order", orders)
        return {"status": "ok"}


class C(StateMachine):
    async def _run(self, wrapped_metadata):
        orders = wrapped_metadata.get("order") or []
        orders.append("C")
        wrapped_metadata.set("order", orders)
        return {"status": "ok"}


@pytest.mark.asyncio
async def test_fallback_next_state_by_order():
    pb = Playbook({
        "initial": "A",
        "final": ["C"],
        "states": [
            {"name": "A"},   # no to / no switch → fallback to B
            {"name": "B"},   # fallback to C
            {"name": "C"}    # final
        ],
        "registry": {
            "A": A,
            "B": B,
            "C": C
        }
    })

    ctx = Ctx()
    orch = Orchestrator(playbook=pb, ctx=ctx)

    result = await orch.run()

    assert result["final_state"] == "C"
    assert result["metadata"]["order"] == ["A", "B", "C"]