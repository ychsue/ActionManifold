import asyncio

import pytest
from am_core.interactive.adapters.fake_adapter import FakeAdapter
from am_core.playbook import Playbook
from am_core.runtime_cli.cli import init_project
from am_core.world import World

@pytest.mark.asyncio
async def test_interactive_simulate_pause_and_resume(tmp_path):
    # 1. run am-run init
    init_project(str(tmp_path))
    pb_data = {
        "initial": "step1",
        "final": ["step2"],
        "states": [
            {"name": "step1", "class_": ".states.step1.Step1", "to": "step2"},
            {"name": "step2", "class_": ".states.step2.Step2"},
        ],
    }
    pb = Playbook(pb_data, base_path=str(tmp_path))
    world = World(pb)
    world.root.ctx.set_interactive_adapter(FakeAdapter())
    # 開一個 task 跑 simulate
    task = asyncio.create_task(world.simulate())

    for i in range(2): # 所有的 state 都該呼叫 provide_decision
    # 等到真的收到 wait_for_decision
        while True:
            kinds = [e.get("kind") for e in world.get_event_log()]
            if len(kinds) > 0 and "wait_for_decision" == kinds[-1]:  # 最後一個 event 是 wait_for_decision，代表正在等決策
                break
            await asyncio.sleep(0.01)

        world.root.provide_decision({"action": "continue"})
        await asyncio.sleep(0.1)  # 等一下讓事件處理完
        

    result = await task
    assert result["final_state"] == "step2"