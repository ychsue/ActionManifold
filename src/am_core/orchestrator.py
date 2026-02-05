# src/am_core/orchestrator.py

from __future__ import annotations
from typing import Any, Dict, List, Optional

import asyncio

from .context import Ctx
from .run_watcher import run_watcher
from .decision_block import decision_block
from .playbook import Playbook


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
    def _instantiate_child(self, state_name: str, child_ctx: Ctx, ctor: Dict[str, Any]):
        kind = ctor["kind"]

        if kind == "python":
            cls = ctor["class"]
            return cls(ctx=child_ctx, parent=self)

        if kind == "orchestrator":
            cls = ctor["class"]
            cls = Orchestrator if cls is None else cls
            sub_pb = ctor["playbook"]
            return cls(playbook=sub_pb, ctx=child_ctx, parent=self)

        if kind == "world":
            sub_pb = ctor["playbook"]
            workdir = ctor.get("workdir")
            world_ctx = child_ctx.child(workdir=workdir)
            return Orchestrator(playbook=sub_pb, ctx=world_ctx, parent=self)

        raise ValueError(f"Unknown constructor kind for state {state_name}: {kind}")

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