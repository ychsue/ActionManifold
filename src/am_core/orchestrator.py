from inspect import isclass

from am_core.feature.feature_unit import feature_unit
from .leak_monitor import LeakMonitor, leak_orch_checked_run
from .context import OrchCtx, StateCtx, CtxBus, WorldCtx
from pathlib import Path
from typing import Optional

@feature_unit(
    belongs_to=["RuntimeEngine"],
    status="planned",
    display_name="Orchestrator Execution",
    notes="執行 playbook，驅動 StateMachine / 子 Orchestrator，並維護 OrchCtx"
)
class Orchestrator:
    """
    Orchestrator 負責依照 playbook 執行整個 workflow。
    """
    playbook: dict
    def __init__(self, name, playbook: dict, parent_orch: Optional["Orchestrator"], worldCtx: WorldCtx, ctxBus: CtxBus):
        LeakMonitor.track_orchestrator(self)
        self.name = name
        self.playbook = playbook
        self.parent_orch = parent_orch
        self.worldCtx = worldCtx
        self.ctxBus = ctxBus
        self.orchCtx = OrchCtx(name, parent_orch.orchCtx if parent_orch else None)

    def report(self, event):
        # bubble to parent orchestrator
        if self.parent_orch:
            self.parent_orch.report(event)
        else:
            # top-level → worldCtx
            self.worldCtx.log_event(event)

        # broadcast to ctxBus
        self.ctxBus.publish(event)
        
    def cleanup(self):
        self.orchCtx.children.clear()
        self.orchCtx.parent = None

    # @leak_orch_checked_run
    async def run(self, auto_sequence=True):
        current = self.playbook["initial"]
        final_states = self.playbook.get("final", [])
        states = self.playbook["states"]

        while True:
            cls = self.playbook["registry"][current]

            # 子 orchestrator
            if isclass(cls) and issubclass(cls, Orchestrator):
                child = cls(
                    name=f"{self.name}.{current}",
                    playbook=cls.playbook,
                    parent_orch=self,
                    worldCtx=self.worldCtx,
                    ctxBus=self.ctxBus,
                )
                self.orchCtx.add_child(child.orchCtx)
                await child.run()

            # atomic state
            else:
                sm_ctx = StateCtx(f"{self.name}.{current}", self.orchCtx)
                self.orchCtx.add_child(sm_ctx)
                sm = cls(sm_ctx, self)
                await sm.run()
                # merge stateCtx → orchCtx
                self.orchCtx.exposure.update(sm_ctx.exposure)


            # 如果是終止 state，結束執行
            if current in final_states:
                break

            # 找下一個 state
            next_state = self._next_state(current)
            if not next_state:
                if not auto_sequence:
                    break
                # if no next state, choose the next state in `states` list
                current_index = states.index(current)
                if current_index + 1 < len(states):
                    current = states[current_index + 1]
                else:
                    break
            else:
                current = next_state

    def _next_state(self, current):
        transitions = self.playbook.get("transitions", [])
        for t in transitions:
            if t["from"] != current:
                continue

            cond = t.get("condition")
            if not cond:
                return t["to"]

            cond_fn = self.playbook["condition_registry"].get(cond)
            if cond_fn and cond_fn(self.orchCtx):
                return t["to"]

        return None
