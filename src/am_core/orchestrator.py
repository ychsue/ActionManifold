# src/am_core/orchestrator.py

from __future__ import annotations
from dataclasses import dataclass, field
import string
from typing import Any, Dict, List, Literal, Optional

import asyncio

from am_core.state_machine import StateMachine

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
    event_log_resume: List[Dict[str, Any]] = field(default_factory=list) # for resume: store the events that are before the resume_from point
    pointer: int = 0 # pointer of event_log for replay/resume/simulate
    stop_at: Optional[str] = None # state name to stop at
    decision_override: Dict[str, Any] = field(default_factory=dict)
    level: Literal["orch", "state", "sm"] = "orch"
    resume_from_event_id: Optional[str] = None
    exec_status: Optional[Literal["replay", "running", "stopped"]] = "running"
    unpaired_event_ids: List[str] = field(default_factory=list) # for resume: store event ids that does not have an after_decision yet
    
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
        if self.ctx.get("root_ctx") is None:
            self.ctx.set("root_ctx", {"i_th": 0})
        rehearsal: Rehearsal = self.ctx.get("rehearsal")
        if rehearsal.mode in ["resume"] and rehearsal.event_log_resume == []:
            prepare_resume(rehearsal)
        
        self.replay_events = [
            ev for ev in rehearsal.event_log
            if ev.get("parent_state") == self.ctx.get("current_state")
        ]
        self.replay_pointer = 0
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
    # replay helper
    # -------------------------
    def _replay_current_event(self):
        if self.replay_pointer < len(self.replay_events):
            return self.replay_events[self.replay_pointer]
        return None
    
    # -------------------------
    # 主 runtime loop
    # -------------------------
    async def run(self, metadata: Optional[Dict[str, Any]] = None, mode: str = "normal") -> Dict[str, Any]:
        """
        執行整個 playbook。

        語意：
        - 從 initial_state 開始
        - 對每個 state：
            - 透過 Playbook 取得 constructor info
            - instantiate child（SM / Orchestrator / World）
            - await child.run(metadata, mode=mode)
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
            # 1. 根據 rehearsal 決定是要記錄還是取回 event，以及是否要真正執行 child
            restore_event, pass_execution, next_exec_status = self._decide_execution_mode(rehearsal, current_state)
            rehearsal.exec_status = next_exec_status

            event_id = self.before_ini_child(
                current_state, 
                parent_state, 
                rehearsal, restore_event=restore_event,)

            state_def, child_ctx, child = self.ini_child(current_state, parent_state)

            enriched = {}
            next_state = None
            if not pass_execution:
                sm_output, timeout_flag, start_time, end_time = await self.exec_child(state_def, child, loop, mode=mode)

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
                                
            next_state = self.after_decision(event_id, metadata, current_state, parent_state, enriched, child_ctx, next_state, rehearsal, restore_event=restore_event)

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
            "events": self.events, # 目前只有 run 會輸出
        }
        
    def before_ini_child(self, current_state: str, parent_state:str, rehearsal: Rehearsal, restore_event: bool) -> str:
        root_ctx = self.ctx.get("root_ctx")
        root_ctx["i_th"] += 1
        
        if restore_event:
            ev = self._replay_current_event()
            if ev is None:
                raise RuntimeError("Replay pointer out of range")

            if ev["kind"] != "before_ini_child":
                raise RuntimeError("Replay mismatch: expected before_ini_child")

            event_id = ev["id"]

            # mimic: 不 emit、不 append
            self.replay_pointer += 1
        else:
            event_id = generate_event_id()+f"-{root_ctx.get('i_th')-1}"
            loop_event = {
                    "id": event_id,
                    "kind": "before_ini_child",
                    "state": current_state,
                    "parent_state": parent_state,
                    "timestamp": time.time(),
                }
            self.emit(loop_event)
            rehearsal.event_log.append(loop_event)
        
        return event_id

    def ini_child(self, current_state: str, parent_state:str) -> tuple[Dict[str, Any], Ctx, Orchestrator | StateMachine]:
        state_def = self.playbook.get_state_def(current_state)
        ctor = self.playbook.get_state_constructor(current_state)
        # child ctx：可在此加入 state-specific override
        child_ctx = self.ctx.child(current_state=current_state, parent_state=parent_state)
        child = self._instantiate_child(current_state, child_ctx, ctor)
        
        return state_def, child_ctx, child
    
    async def exec_child(self, state_def: Dict[str, Any], child: Orchestrator | StateMachine, loop: asyncio.AbstractEventLoop, mode: str) -> tuple[Dict[str, Any], bool, float, float]:
        timeout_setting = state_def.get("timeout")
        timeout_flag = False
        start_time = loop.time()
        try:
            if timeout_setting is not None:
                sm_output = await asyncio.wait_for(
                    child.run(self.metadata, mode=mode),
                    timeout=float(timeout_setting),
                )
            else:
                sm_output = await child.run(self.metadata, mode=mode)
        except asyncio.TimeoutError:
            sm_output = {"status": "timeout"}
            timeout_flag = True
        end_time = loop.time()
        
        return sm_output, timeout_flag, start_time, end_time
    
    def after_decision(self, event_id: str, metadata: Dict[str, Any], current_state: str, parent_state: str, enriched: Dict[str, Any], child_ctx: Ctx, next_state: str|None, rehearsal: Rehearsal, restore_event: bool) -> str|None:
        if restore_event:
            ev = self._replay_current_event()
            if ev is None:
                raise RuntimeError("Replay pointer out of range")

            if ev["kind"] != "after_decision":
                raise RuntimeError("Replay mismatch: expected after_decision")

            # --- mimic ctx_delta ---
            if ev.get("ctx_delta"):
                child_ctx.apply_writes(ev["ctx_delta"])

            # --- mimic metadata ---
            if ev.get("metadata"):
                self.metadata = ev["metadata"]

            # --- mimic next_state ---
            next_state = ev["transition"]

            # 不 emit、不 append
            self.replay_pointer += 1
            return next_state
        else:
            sm_output = enriched.get("output", {})
            exit_event = {
                "id": event_id,
                "kind": "after_decision",
                "timestamp": time.time(),
                "state": current_state,
                "parent_state": parent_state,
                "status": sm_output.get("status"),
                "sm_output": sm_output,
                "metadata": metadata.copy() if metadata else None,
                "ctx_delta": child_ctx.dump_writes() if hasattr(child_ctx, "dump_writes") else None,
                "transition": next_state,
            }
            self.emit(exit_event)
            rehearsal.event_log.append(exit_event)
            return next_state
        
    def get_current_id(self, pointer: int) -> Optional[str]:
        if pointer < len(self.replay_events):
            return self.replay_events[pointer].get("id")
        return None

    def get_current_state_name(self, pointer: int) -> Optional[str]:
        if pointer < len(self.replay_events):
            return self.replay_events[pointer].get("state")
        return None

    def _decide_execution_mode(self, rehearsal: Rehearsal, current_state: str) -> tuple[bool, bool, Literal["replay", "running", "stopped", None]]:
        """
        回傳：
        - restore_event: 是否從 event_log mimic
        - pass_execution: 是否跳過 child.run
        - next_exec_status: replay / running / stopped
        """

        # --- NORMAL 模式 ---
        if rehearsal.mode == "normal":
            return False, False, rehearsal.exec_status

        # --- REPLAY 模式 ---
        if rehearsal.mode == "replay":
            return True, True, rehearsal.exec_status

        # --- RESUME 模式 ---
        pointer = self.replay_pointer
        current_event_id = self.get_current_id(pointer)

        # 1. replay 階段：補前半段
        if rehearsal.exec_status == "replay":
            if current_event_id not in rehearsal.unpaired_event_ids:
                # 這個 event 已經完整（before+after），可以 mimic
                return True, True, "replay"
            else:
                # 這個 event 是中斷點
                if current_event_id == rehearsal.resume_from_event_id:
                    # 切換到 running
                    return False, False, "running"
                else:
                    # 還沒到 resume_from_event_id
                    return False, False, "replay"

        # 2. running 階段：執行後半段
        if rehearsal.exec_status == "running":
            # 若有 stop_at，遇到該 state 就停止
            if rehearsal.stop_at is not None and current_state == rehearsal.stop_at:
                return True, True, "stopped"
            return False, False, "running"

        # 3. stopped 階段：mimic 後續
        if rehearsal.exec_status == "stopped":
            return True, True, "stopped"

        raise RuntimeError("Unknown exec_status")
        
def prepare_resume(rehearsal: Rehearsal):
    """
    1. 若有 resume_from_event_id，則找到第一個 id 為 resume_from_event_id 的 event，而且他得有 after_decision（代表這個 state 已經執行完），就將他(連同after_decision)後面的events_log都去除後暫存，若沒有找到則不處理。
    2. 找到所有沒有 after_decision 的 event，將這些 event 的 id 收集起來，暫存為 unpaired_event_ids。
    3. 將此 unpaired_event_ids 存到 rehearsal.unpaired_event_ids，代表這些 event 是要執行完才會有 after_decision 的。
    """
    
    # 將 rehearsal 狀態改為 replay，讓 Orchestrator.run() 知道現在是在 replay 模式（因為resume一開始就是 replay）
    rehearsal.exec_status = "replay"
    
    # 1. 處理 resume_from_event_id：找到指定 event，並將其之前的 event 存起來
    if rehearsal.resume_from_event_id:
        resume_from_index = None
        for i, ev in enumerate(rehearsal.event_log):
            if ev.get("id") == rehearsal.resume_from_event_id and ev.get("kind") == "before_ini_child":
                # 找到 resume_from_event_id 的 event 了，但要確定他有 after_decision（代表這個 state 已經執行完了）
                stop_event_id = ev.get("id")
                has_after_decision = any(
                    e for e in rehearsal.event_log
                    if e.get("kind") == "after_decision" and e.get("id") == stop_event_id
                )
                if has_after_decision:
                    resume_from_index = i
                    break
        if resume_from_index is not None:
            # 找到了 resume_from_event_id，且他有 after_decision，那就把他之前的 event 都存到 event_log_resume，之後 resume 就只用 event_log_resume
            rehearsal.event_log_resume = rehearsal.event_log[0:resume_from_index+1] # 只存到 resume_from_event_id 的 event 就好，因為 resume_from_event_id 代表的 state 已經執行完了，之後的 event 就不應該被 replay 了
    
    if not rehearsal.event_log_resume: # 如果沒有指定 resume_from_event_id，或是指定了但找不到，那就把整個 event_log 當作 event_log_resume
        rehearsal.event_log_resume = rehearsal.event_log.copy()
        
    # 2. find unpaired events：找到所有沒有 after_decision 的 event，將這些 event 的 id 收集起來，暫存為 unpaired_event_ids
    unpaired_event_ids = set()
    for ev in rehearsal.event_log_resume:
        if ev.get("kind") == "before_ini_child":
            unpaired_event_ids.add(ev.get("id"))
        elif ev.get("kind") == "after_decision":
            event_id = ev.get("id")
            if event_id in unpaired_event_ids:
                unpaired_event_ids.remove(event_id)
    
    # 3. 將此 unpaired_event_ids 存到 rehearsal.unpaired_event_ids，代表這些 event 是要執行完才會有 after_decision 的
    rehearsal.unpaired_event_ids = list(unpaired_event_ids)

