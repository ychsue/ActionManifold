# tests/runtime/test_orchestrator.py

import pytest

from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine


class StartState(StateMachine):
    async def _run(self, metadata):
        # 永遠 ok，線性到 NextState
        self.emit({"type": "state", "name": "StartState"})
        return {"status": "ok"}


class NextState(StateMachine):
    async def _run(self, metadata):
        # 第一次 fail → retry
        # 第二次 ok → Success
        retries = metadata.get("retries", {}).get("NextState", 0)
        self.emit({"type": "state", "name": "NextState", "retries": retries})
        if retries == 0:
            return {"status": "fail"}
        return {"status": "ok"}


example_playbook = {
    "initial": "StartState",
    "final": ["Success", "Error"],
    "states": [
        {
            "name": "StartState",
            "to": "NextState",
        },
        {
            "name": "NextState",
            "timeout": 1.0,
            "retry_times": 3,
            "switch": {
                "ok": "Success",
                "fail": "Error",
                "timeout": "Error",
                "retry": "StartState",
            },
        },
    ],
    "registry": {
        "StartState": StartState,
        "NextState": NextState,
    },
}


@pytest.mark.asyncio
async def test_orchestrator_runs_with_retry_and_success():
    ctx = Ctx()
    pb = Playbook(example_playbook)
    orch = Orchestrator(playbook=pb, ctx=ctx)

    result = await orch.run()

    # 最終應該停在 Success
    assert result["final_state"] == "Success"

    # metadata 應該記錄至少一次 retry
    assert result["metadata"]["retries"]["NextState"] >= 1

    # event log 應該有多個 state 執行紀錄
    events = result["events"]
    assert len(events) >= 2

    states = [e["state"] for e in filter(lambda ev: isinstance(ev.get("state"), str), events)]
    assert "StartState" in states
    assert "NextState" in states