# tests/runtime/test_builtin_states.py

import pytest

from am_core.context import Ctx
from am_core.playbook import Playbook
from am_core.orchestrator import Orchestrator


@pytest.mark.asyncio
async def test_builtin_success_state():
    pb = Playbook({
        "initial": "Success",
        "final": ["Success"],
        "states": [
            {"name": "Success"}
        ]
    })

    ctx = Ctx()
    orch = Orchestrator(playbook=pb, ctx=ctx)
    result = await orch.run()

    assert result["final_state"] == "Success"


@pytest.mark.asyncio
async def test_builtin_error_state():
    pb = Playbook({
        "initial": "Error",
        "final": ["Error"],
        "states": [
            {"name": "Error"}
        ]
    })

    ctx = Ctx()
    orch = Orchestrator(playbook=pb, ctx=ctx)
    result = await orch.run()

    assert result["final_state"] == "Error"


@pytest.mark.asyncio
async def test_builtin_fail_state():
    pb = Playbook({
        "initial": "Fail",
        "final": ["Fail"],
        "states": [
            {"name": "Fail"}
        ]
    })

    ctx = Ctx()
    orch = Orchestrator(playbook=pb, ctx=ctx)
    result = await orch.run()

    assert result["final_state"] == "Fail"