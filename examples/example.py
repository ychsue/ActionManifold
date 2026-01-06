from sympy import im
from am_core.state_machine import StateMachine, WorldRunner
from am_core.orchestrator import Orchestrator
from am_core.context import WorldCtx, CtxBus
from pathlib import Path
from am_core.leak_monitor import LeakMonitor
import asyncio

class InputName(StateMachine):
    async def run(self):
        self.emit("progress", {"msg": "開始輸入名稱"})
        self.ctx.set("name_entered", True)
        self.emit("progress", {"msg": "名稱輸入完成"})

class KeyIn(StateMachine):
    async def run(self):
        self.emit("progress", {"msg": "輸入密碼中"})
        self.ctx.set("password", "1234")

class Check(StateMachine):
    async def run(self):
        pwd = self.ctx.get("password")
        if pwd == "1234":
            self.ctx.set("password_ok", True)
        else:
            self.ctx.set("password_bad", True)

class Success(StateMachine):
    async def run(self):
        self.emit("progress", {"msg": "密碼正確"})

class Error(StateMachine):
    async def run(self):
        self.emit("progress", {"msg": "密碼錯誤"})

input_password_playbook = {
    "name": "InputPasswordFlow",
    "initial": "KeyIn",
    "final": ["Success", "Error"],
    "states": ["KeyIn", "Check", "Success", "Error"],
    "transitions": [
        {"from": "KeyIn", "to": "Check"},
        {"from": "Check", "to": "Success", "condition": "password_ok"},
        {"from": "Check", "to": "Error",   "condition": "password_bad"}
    ],
    "registry": {
        "KeyIn": KeyIn,
        "Check": Check,
        "Success": Success,
        "Error": Error
    },
    "condition_registry": {
    "password_ok": lambda ctx: ctx.get("password") == "1234",
    "password_bad": lambda ctx: ctx.get("password") != "1234",
    }
}

class InputPasswordFlow(Orchestrator):
    playbook = input_password_playbook

login_playbook = {
    "name": "LoginFlow",
    "initial": "InputName",
    "states": ["InputName", "InputPasswordFlow"],
    "transitions": [],
    "registry": {
        "InputName": InputName,
        "InputPasswordFlow": InputPasswordFlow
    }
}
async def run_demo():
    run_dir = Path("runs") / "run-0004"
    ctxBus = CtxBus()
    worldCtx = WorldCtx("LoginWorkflow", "run-0004", run_dir)
    
    root_orch = Orchestrator(
        name="LoginFlow",
        playbook=login_playbook,
        parent_orch=None,
        worldCtx=worldCtx,
        ctxBus=ctxBus,
    )

    await root_orch.run()
    worldCtx.dump()
    root_orch.orchCtx.print_ctx_tree()

    print("=== Event Log ===")
    for e in worldCtx.event_log:
        print(e)
        
    # Cleanup references to help with leak detection
    root_orch.cleanup()
    del root_orch
    LeakMonitor.check()
    
async def run_demo_with_worldrunner():
    run_dir = Path("runs") / "run-0005"
    world_runner = WorldRunner( workflow_id="LoginWorkflow", run_id="run-0005", run_dir=run_dir, playbook=login_playbook, ctx=None, orchestrator=None)

    await world_runner.run()
    print("=== Event Log ===")
    if world_runner.inner_world and world_runner.inner_orch:
        for e in world_runner.inner_world.event_log:
            print(e)
        # Cleanup references to help with leak detection
        world_runner.inner_orch.cleanup()
        del world_runner
        LeakMonitor.check()
    else:
        print("No inner world or orchestrator found.")
if __name__ == "__main__":
    asyncio.run(run_demo_with_worldrunner()) 