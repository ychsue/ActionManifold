from pathlib import Path

from sympy import Le
from ActionManifold.orchestrator import Orchestrator
from ActionManifold.context import WorldCtx, CtxBus
from ActionManifold.state_machine import StateMachine, WorldRunnerFactory
from ActionManifold.leak_monitor import LeakMonitor
import asyncio

class InputNameMachine(StateMachine):
    async def run(self):
        self.emit("progress", {"msg": "開始輸入名稱"})
        self.ctx.set("name_entered", True)
        self.emit("progress", {"msg": "名稱輸入完成"})
class InputPasswordMachine(StateMachine):
    async def run(self):
        self.emit("progress", {"msg": "開始輸入密碼"})
        self.ctx.set("password", "1234")
        self.emit("progress", {"msg": "密碼輸入完成"})
        # 密碼檢查
        pwd = self.ctx.get("password")
        if pwd == "1234":
            self.ctx.set("password_ok", True)
            self.emit("progress", {"msg": "密碼正確"})
        else:
            self.ctx.set("password_bad", True)
            self.emit("progress", {"msg": "密碼錯誤"})

login_playbook = {
    "states": ["InputName", "InputPasswordFlow"],
    "initial": "InputName",
    "registry": {
        "InputName": InputNameMachine,
        "InputPasswordFlow": InputPasswordMachine,
    }
}

class ERPProcessMachine(StateMachine):
    async def run(self):
        self.emit("progress", {"msg": "開始處理 ERP 資料"})
        # 模擬資料處理
        await asyncio.sleep(1)
        self.emit("progress", {"msg": "ERP 資料處理完成"})
class FetchDataMachine(StateMachine):
    async def run(self):
        self.emit("progress", {"msg": "開始擷取 ERP 資料"})
        # 模擬資料擷取
        await asyncio.sleep(1)
        self.emit("progress", {"msg": "ERP 資料擷取完成"})

erp_playbook = {
    "states": ["FetchData", "ProcessData"],
    "initial": "FetchData",
    "registry": {
        "FetchData": FetchDataMachine,  # placeholder
        "ProcessData": ERPProcessMachine,  # placeholder
    }
}


master_playbook = {
    "initial": "RunLoginWorld",
    "states": ["RunLoginWorld", "RunERPWorld"],
    "transitions": [
        {"from": "RunLoginWorld", "to": "RunERPWorld"},
    ],
    "registry": {
        "RunLoginWorld": WorldRunnerFactory(
            workflow_id="LoginWorkflow",
            run_id="login-run-001",
            run_dir=Path("runs/login-run-001"),
            playbook=login_playbook,
        ).build(),
        "RunERPWorld": WorldRunnerFactory(
            workflow_id="ERPWorkflow",
            run_id="erp-run-001",
            run_dir=Path("runs/erp-run-001"),
            playbook=erp_playbook,
        ).build(),
    }
}

async def demo_world_to_world():
    ctxBus = CtxBus()
    world = WorldCtx("MasterWorkflow", "master-run-001", Path("runs/master-run-001"))

    master_orch = Orchestrator(
        name="MasterFlow",
        playbook=master_playbook,
        parent_orch=None,
        worldCtx=world,
        ctxBus=ctxBus,
    )

    await master_orch.run()

    print("=== Master Event Log ===")
    for e in world.event_log:
        print(e)
    world.dump()

    master_orch.cleanup()
    del master_orch
    print("After master_orch deleted:")
    LeakMonitor.check()
        
if __name__ == "__main__":
    asyncio.run(demo_world_to_world())