from turtle import st

from am_core.feature.feature_unit import feature_unit
from .context import StateCtx, WorldCtx, CtxBus, OrchCtx
from .orchestrator import Orchestrator
from pathlib import Path
from typing import Any, Optional

class StateMachine:
    def __init__(self, ctx: StateCtx, orchestrator: Orchestrator):
        self.ctx = ctx
        self.orch = orchestrator

    def emit(self, type_, payload):
        evt = {
            "type": type_,
            "source": self.ctx.name,
            "payload": payload,
        }
        self.orch.report(evt)

@feature_unit(
    belongs_to=["RuntimeEngine"],
    status="planned",
    display_name="World Runner",
    depends=[Orchestrator.run],
    notes="建立 WorldCtx + root Orchestrator，執行整個世界並 dump 狀態"
)        
class WorldRunner(StateMachine):
    """
    對外：像一個 StateMachine（有 run / replay / resume）
    對內：負責建立 WorldCtx + root Orchestrator，並執行整個世界。
    """

    def __init__(self, ctx: Optional[StateCtx], orchestrator: Optional[Orchestrator], workflow_id:str, run_id:str, run_dir: Path, playbook: dict):
        if orchestrator is None:
            # 建立一個臨時的 orchestrator，用來持有 CtxBus
            dummy_world = WorldCtx("dummy","dummy", run_dir)
            temp_orch = Orchestrator("TempWorldRunnerOrch", {}, None, dummy_world, CtxBus())
            temp_ctx = StateCtx("TempWorldRunnerCtx", temp_orch.orchCtx)
            ctx = temp_ctx
            orchestrator = temp_orch
        if ctx is None:
            ctx = StateCtx("TempWorldRunnerCtx", orchestrator.orchCtx)
        # 將此 ctx 傳給父類別
        orchestrator.orchCtx.add_child(ctx)
        
        super().__init__(ctx, orchestrator)
        self.workflow_id = workflow_id
        self.run_id = run_id
        self.run_dir = Path(run_dir)
        self.playbook = playbook
        self.inner_world = None  # WorldCtx
        self.inner_orch = None  # Orchestrator

    def _build_world(self):
        self.inner_world = WorldCtx(self.workflow_id, self.run_id, self.run_dir)

    def _build_root_orchestrator(self):
        if self.inner_world is None:
            self._build_world()
            if self.inner_world is None:
                raise RuntimeError("WorldRunner 未正確建立 world")
        self.inner_orch = Orchestrator(
            name=self.workflow_id,
            playbook=self.playbook,
            parent_orch=None,
            worldCtx=self.inner_world,
            ctxBus=self.orch.ctxBus,  # 用外層 orchestrator 的 bus
        )

    async def run(self):
        # 世界級事件：進入世界
        self.orch.report({
            "type": "enter_world",
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "run_dir": str(self.run_dir),
        })

        # 建立世界 + root orchestrator
        self._build_world()
        self._build_root_orchestrator()
        if self.inner_orch is None or self.inner_world is None:
            raise RuntimeError("WorldRunner 未正確建立 world 或 root_orch")

        status = "unknown"
        try:
            # 執行整個世界
            await self.inner_orch.run()

            status = "success"

        except Exception as e:
            status = "error"
            self.inner_world.state["exception"] = str(e)
            raise

        finally:
            # dump 世界
            self.inner_world.dump()

            # 世界級事件：離開世界
            self.orch.report({
                "type": "exit_world",
                "workflow_id": self.workflow_id,
                "run_id": self.run_id,
                "status": status,
            })

            # 把結果寫回 ctx
            self.ctx.set("world_run_id", self.inner_world.run_id)
            self.ctx.set("world_dir", str(self.inner_world.run_dir))
            self.ctx.set("world_state", self.inner_world.state)

        # 清掉 temp orchestrator（避免 leak）
        if self.orch.name == "TempWorldRunnerOrch":
            self.orch.cleanup()


    def replay(self):
        # 重新載入世界，重播 event_log（這裡先給骨架）
        self.inner_world = WorldCtx.load(self.run_dir, run_id= self.run_id)
        # 這裡可以做：重播 event_log、重建視覺化、或做分析
        return self.inner_world.event_log

    async def resume(self, new_run_id):
        """
        用舊世界的 dump 當作起點，繼續跑新的 run。
        """
        old_world = WorldCtx.load(self.run_dir, run_id= self.run_id)
        self.run_id = new_run_id
        self.run_dir = self.run_dir.parent.parent / new_run_id

        # 建立新的世界，繼承舊世界的 state
        self.inner_world = WorldCtx(self.workflow_id, self.run_id, self.run_dir)
        self.inner_world.state.update(old_world.state)

        # 繼續跑（可以選擇從某個 state 開始，這裡先簡化成重新跑）
        self._build_root_orchestrator()
        if self.inner_orch is None:
            raise RuntimeError("WorldRunner 未正確建立 root_orch")
        await self.inner_orch.run()
        self.inner_world.dump()

class WorldRunnerFactory:
    def __init__(self, workflow_id, run_id, run_dir, playbook):
        self.workflow_id = workflow_id
        self.run_id = run_id
        self.run_dir = run_dir
        self.playbook = playbook

    def build(self):
        factory = self

        class _WorldRunner(StateMachine):
            def __init__(self, ctx, orchestrator):
                super().__init__(ctx, orchestrator)
                self.wr = WorldRunner(
                    ctx=ctx,
                    orchestrator=orchestrator,
                    workflow_id=factory.workflow_id,
                    run_id=factory.run_id,
                    run_dir=factory.run_dir,
                    playbook=factory.playbook,
                )
            async def run(self):
                await self.wr.run()
                # merge world state into ctx
                self.ctx.set("world", self.wr.inner_world)
        return _WorldRunner