# src/am_core/orchestrator.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional

import asyncio

from .context import Ctx
from .run_watcher import run_watcher
from .decision_block import decision_block
from .playbook import Playbook
from .utils import generate_event_id
import time

@dataclass
class Rehearsal:
    mode: Literal["normal", "replay", "resume", "simulate"] = "normal"
    event_log: List[Dict[str, Any]] = field(default_factory=list)
    pointer: int = 0
    stop_at: Optional[str] = None
    decision_override: Dict[str, Any] = field(default_factory=dict)
    level: Literal["orch", "state", "sm"] = "orch"

    def advance(self):
        self.pointer += 1

    def current_event(self):
        if self.pointer < len(self.event_log):
            return self.event_log[self.pointer]
        return None

class Orchestrator:
    """
    語意：
    - Orchestrator 是「官能基」：執行多個 child（SM / Orchestrator / World）
    - 有 ctx（lexical scope）
    - 有 parent（可選，用於事件冒泡）
    - 對外介面：async run(metadata) -> dict
    - emit(event)：自己收集，並往 parent 冒泡
    """

    def __init__(
        self,
        playbook: Playbook,
        ctx: Ctx,
        parent: Optional[Any] = None,
        *,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.playbook = playbook
        self.ctx = ctx
        self.parent = parent

        self.metadata: Dict[str, Any] = metadata or {}
        self.events: List[Dict[str, Any]] = []
        if self.ctx.get("rehearsal") is None:
            self.ctx.set("rehearsal", Rehearsal())

    # -------------------------
    # 事件冒泡
    # -------------------------
    def emit(self, event: Dict[str, Any]) -> None:
        self.events.append(event)
        if self.parent and hasattr(self.parent, "emit"):
            self.parent.emit(event)

    # -------------------------
    # child instantiate（依 ctor info）
    # -------------------------
    def _instantiate_child(self, state_name: str, child_ctx: Ctx, ctor: dict):
        """
        ctor = {
            "class": PythonClass,
            "subflow": Optional[Playbook],
            "workdir": Optional[str],
        }

        語意：
        - 若 class 是 Orchestrator → 用 subflow 當 playbook 建立子 orchestrator
        - 若 class 是 StateMachine → 直接建立 SM
        - 若 class 是 WorldStateMachine（未來）→ 也能自然支援
        """

        cls = ctor["class"]
        subflow = ctor.get("subflow")
        workdir = ctor.get("workdir")

        # Orchestrator（含自訂 orchestrator class）
        from .orchestrator import Orchestrator  # 避免循環 import

        if issubclass(cls, Orchestrator):
            if subflow is None:
                raise ValueError(f"State {state_name} uses Orchestrator but no subflow provided")
            return cls(
                playbook=subflow,
                ctx=child_ctx,
                parent=self,
            )

        # StateMachine（一般 SM）
        from .state_machine import StateMachine

        if issubclass(cls, StateMachine):
            # 若未來 WORLD 要用 workdir，可在這裡 child_ctx.child(workdir=...)
            return cls(
                ctx=child_ctx,
                parent=self,
            )

        raise TypeError(f"Unsupported constructor class for state {state_name}: {cls}")
    
    # -------------------------
    # 主 runtime loop
    # -------------------------
    async def run(self, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        執行整個 playbook。

        語意：
        - 從 initial_state 開始
        - 對每個 state：
            - 透過 Playbook 取得 constructor info
            - instantiate child（SM / Orchestrator / World）
            - await child.run(metadata)
            - run_watcher(...)
            - emit(event)
            - decision_block(...) → next_state
        - 若 next_state 是 final 或 None → 結束
        """
        rehearsal: Rehearsal = self.ctx.get("rehearsal")
        if metadata is None:
            metadata = self.metadata
        else:
            # 若外部傳入 metadata，就以外部為主
            self.metadata = metadata

        current_state = self.playbook.initial_state()
        final_state: Optional[str] = None

        loop = asyncio.get_event_loop()
        parent_state = self.ctx.get("current_state")

        while True:
            # final state → 結束
            # if self.playbook.is_final(current_state):
            #     final_state = current_state
                # break
            event_id = generate_event_id()

            loop_event = {
                    "id": event_id,
                    "kind": "loop_entry",
                    "state": current_state,
                    "parent_state": parent_state,
                    "timestamp": time.time(),
                }
            self.emit(loop_event)
            rehearsal.event_log.append(loop_event)

            state_def = self.playbook.get_state_def(current_state)
            ctor = self.playbook.get_state_constructor(current_state)

            # child ctx：可在此加入 state-specific override
            child_ctx = self.ctx.child(current_state=current_state, parent_state=parent_state)

            child = self._instantiate_child(current_state, child_ctx, ctor)

            timeout_setting = state_def.get("timeout")
            timeout_flag = False

            start_time = loop.time()

            try:
                if timeout_setting is not None:
                    sm_output = await asyncio.wait_for(
                        child.run(self.metadata),
                        timeout=float(timeout_setting),
                    )
                else:
                    sm_output = await child.run(self.metadata)
            except asyncio.TimeoutError:
                sm_output = {"status": "timeout"}
                timeout_flag = True

            end_time = loop.time()

            # run_watcher：決定 status + 產生 event
            enriched = run_watcher(
                state_name=current_state,
                state_def=state_def,
                sm_output=sm_output,
                metadata=self.metadata,
                start_time=start_time,
                end_time=end_time,
                timeout_flag=timeout_flag,
                parent_state=parent_state,
            )

            event = enriched["event"]
            self.emit(event)

            # decision_block：決定下一個 state
            next_state = decision_block(
                playbook=self.playbook,
                current_state=current_state,
                enriched_output=enriched,
            )
                                
            # 為了replay/resume 所需要的 event log，必須記錄 decision_block 的輸出（即 next_state）
            event = {
                "id": event_id,
                "kind": "state_exit",
                "timestamp": time.time(),
                "state": current_state,
                "parent_state": parent_state,
                "status": sm_output.get("status"),
                "sm_output": sm_output,
                "metadata": metadata.copy() if metadata else None,
                "ctx_delta": child_ctx.diff(self.ctx) if hasattr(child_ctx, "diff") else None,
                "transition": next_state,
            }
            self.emit(event)
            rehearsal.event_log.append(event)

            if next_state is None:
                final_state = current_state
                break

            # if self.playbook.is_final(next_state): # comment 掉是因為要由 decision_block 決定，好讓 final state 可被執行
            #     final_state = next_state
            #     break

            current_state = next_state

        return {
            "final_state": final_state,
            "metadata": self.metadata,
            "events": self.events,
        }
        
    