# src/am_core/orchestrator.py

from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional
import asyncio
import time
import uuid

from am_core.ctx.ctx_wrapper import CtxDeltaCollector, WrappedCtx
from am_core.runtime_store import RuntimeStore
from am_core.state_machine import StateMachine
from tests.runtime.fake_runtime_store import FakeRuntimeStore
from .ctx.context import Ctx
from .run_watcher import run_watcher
from .decision_block import decision_block
from .playbook import Playbook
from .utils import dynamic_import, dynamic_import_from_base_path, generate_event_id


# ------------------------------------------------------------
# Rehearsal metadata
# ------------------------------------------------------------

@dataclass
class Rehearsal:
    mode: Literal["normal", "replay", "resume", "simulate"] = "normal"
    event_log: List[Dict[str, Any]] = field(default_factory=list)

    # resume 專用
    event_log_resume: List[Dict[str, Any]] = field(default_factory=list)
    resume_from_event_id: Optional[str] = None
    unpaired_event_ids: List[str] = field(default_factory=list)

    # runtime pointer
    pointer: int = 0

    # runtime control
    stop_at: Optional[str] = None
    exec_status: Literal["replay", "running", "stopped"] = "running"

    # decision override（未來用）
    decision_override: Dict[str, Any] = field(default_factory=dict)

    # replay level（目前保留）
    level: Literal["orch", "state", "sm"] = "orch"

    def advance(self):
        self.pointer += 1

    def current_event(self):
        if self.pointer < len(self.event_log):
            return self.event_log[self.pointer]
        return None


# ------------------------------------------------------------
# Orchestrator
# ------------------------------------------------------------

REPLAY_MIMIC = "replay_mimic"
REPLAY_EXECUTE = "replay_execute"
REPLAY_PHASE = "replay"
RUNNING_PHASE = "running"
STOPPED_PHASE = "stopped"


class Orchestrator:
    """
    Orchestrator：執行多個 child（SM / Orchestrator / World）
    """

    def __init__(
        self,
        playbook: Playbook,
        ctx: Ctx,
        runtime_store: RuntimeStore = FakeRuntimeStore(),
        parent: Optional[Any] = None,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        name: Optional[str] = None,
    ) -> None:
        self.playbook = playbook
        self.ctx = ctx
        self.parent = parent
        self.metadata: Dict[str, Any] = metadata or {}
        self.name = name if name else ctx.get("current_state", "root")
        self.events: List[Dict[str, Any]] = []

        # 新增 orchestrator id
        self.orch_id = uuid.uuid4().hex

        # 注入 runtime_store（不依賴 World）
        self.runtime = runtime_store

        # 註冊自己為 active orchestrator
        self.runtime.register_orchestrator(self)
        
        # rehearsal 初始化
        if self.ctx.get("rehearsal") is None:
            self.ctx.set("rehearsal", Rehearsal())

        if self.ctx.get("root_ctx") is None:
            self.ctx.set("root_ctx", {"i_th": 0})

        rehearsal: Rehearsal = self.ctx.get("rehearsal")

        # resume 模式：建構 resume 視野
        if rehearsal.mode == "resume" and rehearsal.event_log_resume == []:
            prepare_resume(rehearsal)

        # nested replay 視野切割
        self.replay_events = [
            ev for ev in rehearsal.event_log
            if ev.get("parent_state") == self.ctx.get("current_state")
        ]
        self.replay_pointer = 0

    # ------------------------------------------------------------
    # event 冒泡
    # ------------------------------------------------------------
    def emit(self, event: Dict[str, Any]) -> None:
        self.events.append(event)
        if self.parent and hasattr(self.parent, "emit"):
            self.parent.emit(event)

    # ------------------------------------------------------------
    # child instantiate
    # ------------------------------------------------------------
    def _instantiate_child(self, state_name: str, child_ctx: Ctx, ctor: dict):
        cls = ctor["class_"]
        subflow = ctor.get("subflow")

        from .orchestrator import Orchestrator

        # class_ 若以 "." 開頭，代表它是相對於當前 playbook.base_path 的 class path。
        # 這類路徑不走一般頂層 import，避免不同 playbook 下的 states.* 彼此污染。
        if isinstance(cls, str) and cls.startswith("."):
            if self.playbook.base_path is None:
                raise ValueError(
                    f"Playbook of {self.name} does not have a base_path, cannot resolve relative class path {cls}"
                )
            cls = dynamic_import_from_base_path(self.playbook.base_path, cls)
                
        if isinstance(cls, str):
            raise ValueError(
                f"State {state_name} has class_ defined as string but is not importable. "
                "Use a relative path starting with '.' or a standard Python absolute import path. "
                f"Got: {cls}"
            )

        if issubclass(cls, Orchestrator):
            if subflow is None:
                raise ValueError(f"State {state_name} uses Orchestrator but no subflow provided")
            return cls(playbook=subflow, ctx=child_ctx,
                       runtime_store=self.runtime,
                       parent=self, name=state_name)

        if issubclass(cls, StateMachine):
            wrapped_ctx = WrappedCtx(child_ctx, CtxDeltaCollector())
            return cls(wrapped_ctx=wrapped_ctx, parent=self, name=state_name)

        raise TypeError(f"Unsupported constructor class for state {state_name}: {cls}")

    def _root(self) -> Any:
        if self.parent is None:
            return self
        elif type(self.parent) == Orchestrator:
            return self.parent._root()
        elif type(self.parent).__name__ == "World":  # 避免直接 import World 導致 circular import
            return self.parent
        else:
            raise TypeError(f"Unknown parent type: {type(self.parent)}")

    # ------------------------------------------------------------
    # replay helper
    # ------------------------------------------------------------
    def _replay_current_event(self):
        if self.replay_pointer < len(self.replay_events):
            return self.replay_events[self.replay_pointer]
        return None

    # ------------------------------------------------------------
    # 主 runtime loop
    # ------------------------------------------------------------
    async def run(self, metadata: Optional[Dict[str, Any]] = None, sm_mode: str = "normal") -> Dict[str, Any]:
        rehearsal: Rehearsal = self.ctx.get("rehearsal")

        if metadata is None:
            metadata = self.metadata
        else:
            self.metadata = metadata

        current_state = self.playbook.initial_state()
        final_state: Optional[str] = None

        loop = asyncio.get_event_loop()
        parent_state = self.ctx.get("current_state")

        while True:
            # ------------------------------------------------------------
            # 1. 決定當前 state 的執行模式（replay / running / stopped）
            # ------------------------------------------------------------
            phase = self._decide_execution_mode(rehearsal, current_state)
            # 預設為 RUNNING_PHASE，但在 replay 模式下會根據 pointer 和 resume_from_event_id 切換到 REPLAY_MIMIC / REPLAY_EXECUTE / STOPPED_PHASE
            restore_event = phase in (REPLAY_PHASE, REPLAY_MIMIC, STOPPED_PHASE)
            pass_execution = phase in (REPLAY_PHASE, REPLAY_MIMIC, STOPPED_PHASE)
            rehearsal.exec_status = REPLAY_PHASE if phase in (REPLAY_MIMIC, REPLAY_EXECUTE) else phase

            # ------------------------------------------------------------
            # 2. before_ini_child
            # ------------------------------------------------------------
            event_id = self.before_ini_child(
                current_state,
                parent_state,
                rehearsal,
                restore_event=restore_event,
            )
            # TODO: 先將 Stop 跳出 loop
            if rehearsal.exec_status == STOPPED_PHASE:
                final_state = current_state
                break
            
            # ------------------------------------------------------------
            # 3. instantiate child
            # ------------------------------------------------------------
            state_def, child_ctx, child = self.ini_child(current_state, parent_state)

            enriched = {}
            next_state = None

            # ------------------------------------------------------------
            # 4. 執行 child.run（若不是 replay/stopped）
            # ------------------------------------------------------------
            isSM = isinstance(child, StateMachine)
            if isSM:    
                self.emit({
                    "kind": "before_sm_execute",
                    "state": current_state,
                    "chain": child.get_chain(),
                    "ctx": child_ctx.dump(),          # 當前 ctx
                    "metadata": dict(self.metadata),  # 當前 metadata
                    "timestamp": time.time(),
                })
            
            if not pass_execution:
                sm_output, timeout_flag, start_time, end_time = await self.exec_child(
                    state_def, child, loop, sm_mode=sm_mode
                )

                # TODO: 不確定未來是否stop要這樣處理，先這樣寫，之後再優化
                if rehearsal.exec_status == STOPPED_PHASE: # 執行後可能會變，所以，需要再檢查一次
                    final_state = current_state
                    break
                
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

                next_state = decision_block(
                    playbook=self.playbook,
                    current_state=current_state,
                    enriched_output=enriched,
                )

            # ------------------------------------------------------------
            # 5. after_decision（mimic 或 record）
            # ------------------------------------------------------------
            next_state = self.after_decision(
                event_id,
                current_state,
                parent_state,
                enriched,
                child_ctx,
                next_state,
                rehearsal,
                restore_event=restore_event,
            )

            # ------------------------------------------------------------
            # 6. 結束條件
            # ------------------------------------------------------------
            if next_state is None:
                final_state = current_state
                break

            current_state = next_state

        # 執行完畢，從 active orchestrators 移除
        self.runtime.unregister_orchestrator(self.orch_id)

        return {
            "final_state": final_state,
            "metadata": self.metadata,
            "events": self.events,
        }

    # ------------------------------------------------------------
    # before_ini_child
    # ------------------------------------------------------------
    def before_ini_child(self, current_state: str, parent_state: str, rehearsal: Rehearsal, restore_event: bool) -> str:
        root_ctx = self.ctx.get("root_ctx")
        root_ctx["i_th"] += 1
        isStopped = rehearsal.exec_status == STOPPED_PHASE

        if restore_event and isStopped is False:
            ev = self._replay_current_event()
            if ev is None:
                raise RuntimeError("Replay pointer out of range")
            if ev["kind"] != "before_ini_child":
                raise RuntimeError("Replay mismatch: expected before_ini_child")

            event_id = ev["id"]
            self.replay_pointer += 1
            return event_id

        # normal / running
        event_id = generate_event_id() + f"-{root_ctx.get('i_th')-1}" if not isStopped else STOPPED_PHASE
        loop_event = {
            "id": event_id,
            "kind": "before_ini_child" if not isStopped else "before_ini_child_stopped",
            "state": current_state,
            "parent_state": parent_state,
            "timestamp": time.time(),
        }
        self.emit(loop_event)
        rehearsal.event_log.append(loop_event)
        return event_id

    # ------------------------------------------------------------
    # ini_child
    # ------------------------------------------------------------
    def ini_child(self, current_state: str, parent_state: str):
        state_def = self.playbook.get_state_def(current_state)
        ctor = self.playbook.get_state_constructor(current_state)
        
        if state_def is None or ctor is None:
            raise ValueError(f"State {current_state} not found in playbook states or registry")
        # 取得 per-state initialization
        child_ctx = self.ctx.child(
            current_state=current_state, 
            parent_state=parent_state,
            **state_def.get("init", {})
        )
        child = self._instantiate_child(current_state, child_ctx, ctor)
        return state_def, child_ctx, child

    # ------------------------------------------------------------
    # exec_child
    # ------------------------------------------------------------
    async def exec_child(self, state_def, child, loop, sm_mode):
        timeout_setting = state_def.get("timeout")
        timeout_flag = False
        start_time = loop.time()
        
        child_metadata = self.metadata if state_def.get("use_parent_metadata", False) or isinstance(child, StateMachine) else None

        try:
            if timeout_setting is not None:
                sm_output = await asyncio.wait_for(
                    child.run(child_metadata, sm_mode=sm_mode),
                    timeout=float(timeout_setting),
                )
            else:
                sm_output = await child.run(child_metadata, sm_mode=sm_mode)
        except asyncio.TimeoutError:
            sm_output = {"status": "timeout"}
            timeout_flag = True

        end_time = loop.time()
        return sm_output, timeout_flag, start_time, end_time

    # ------------------------------------------------------------
    # after_decision
    # ------------------------------------------------------------
    def after_decision(
        self,
        event_id,
        current_state,
        parent_state,
        enriched,
        child_ctx,
        next_state,
        rehearsal,
        restore_event,
    ):
        if restore_event:
            ev = self._replay_current_event()
            if ev is None:
                raise RuntimeError("Replay pointer out of range")
            if ev["kind"] != "after_decision":
                raise RuntimeError("Replay mismatch: expected after_decision")

            if ev.get("ctx_delta"):
                child_ctx.apply_writes(ev["ctx_delta"])

            if ev.get("metadata"):
                self.metadata = ev["metadata"]

            next_state = ev["transition"]
            self.replay_pointer += 1
            return next_state

        # running
        enriched_event = enriched.get("event", {}) or {}
        sm_output = enriched_event.get("output", {}) or {}
        # 如果是SM，要套用 ctx_delta 與 metadata_delta，而 metadata_delta 有可能被 run_watcher 修改（例如 retry 的時候），所以要以 run_watcher 的結果為主
        if sm_output.get("is_SM"):
            if sm_output.get("ctx_delta"):
                child_ctx.apply_writes(sm_output["ctx_delta"], into_writes=True)

            if enriched_event.get("metadata_delta"):
                # 特別處理 retries 的 metadata_delta，因為 metadata["retries"] 是一個 dict，所以他也要用 update 的方式來合併，而不是直接覆蓋
                retries = dict(self.metadata["retries"]) if "retries" in self.metadata else {}
                if "retries" in enriched_event["metadata_delta"]:
                    retries_delta = enriched_event["metadata_delta"]["retries"]
                    retries.update(retries_delta)
                self.metadata.update(enriched_event["metadata_delta"])
                self.metadata["retries"] = retries
        exit_event = {
            "id": event_id,
            "kind": "after_decision",
            "timestamp": time.time(),
            "state": current_state,
            "parent_state": parent_state,
            "status": sm_output.get("status"),
            "sm_output": sm_output,
            "metadata": self.metadata.copy() if self.metadata else None,
            "ctx_delta": child_ctx.dump_writes() if hasattr(child_ctx, "dump_writes") else None,
            "transition": next_state,
        }
        self.emit(exit_event)
        if sm_output.get("is_SM"):
            self.emit({
            "kind": "after_sm_execute",
            "state": current_state,
            "chain": sm_output.get("chain"),
            "ctx_delta": sm_output.get("ctx_delta"),
            "metadata_delta": sm_output.get("metadata_delta"),
            "output": sm_output.get("output"),
            "status": sm_output.get("status"),
            "timestamp": time.time(),
            })

        rehearsal.event_log.append(exit_event)
        
        # 如果是 root orchestrator，就讓 world 寫 snapshot
        root = self._root()
        if hasattr(root, "save_snapshot"):
            root.save_snapshot()        
        
        return next_state

    # ------------------------------------------------------------
    # replay helpers
    # ------------------------------------------------------------
    def get_current_id(self, pointer):
        if pointer < len(self.replay_events):
            return self.replay_events[pointer].get("id")
        return None

    def get_current_state_name(self, pointer):
        if pointer < len(self.replay_events):
            return self.replay_events[pointer].get("state")
        return None

    # ------------------------------------------------------------
    # 決定執行模式（phase）
    # ------------------------------------------------------------
    def _decide_execution_mode(self, rehearsal: Rehearsal, current_state: str):
        # normal
        if rehearsal.mode == "normal":
            if rehearsal.stop_at == current_state:
                return STOPPED_PHASE
            return RUNNING_PHASE

        # replay
        if rehearsal.mode == "replay":
            if rehearsal.stop_at == current_state:
                return STOPPED_PHASE
            return REPLAY_PHASE

        # resume
        return self._decide_resume_phase(rehearsal, current_state)

    # ------------------------------------------------------------
    # resume phase machine
    # ------------------------------------------------------------
    def _decide_resume_phase(self, rehearsal: Rehearsal, current_state: str):
        pointer = self.replay_pointer
        current_event_id = self.get_current_id(pointer)

        # 1. replay 階段
        if rehearsal.exec_status == REPLAY_PHASE:
            if current_event_id not in rehearsal.unpaired_event_ids:
                return REPLAY_MIMIC

            # 遇到 resume_from_event_id → 切換到 running
            if current_event_id == rehearsal.resume_from_event_id:
                return RUNNING_PHASE

            return REPLAY_EXECUTE

        # 2. running 階段
        if rehearsal.exec_status == RUNNING_PHASE:
            if rehearsal.stop_at == current_state:
                return STOPPED_PHASE
            return RUNNING_PHASE

        # 3. stopped 階段
        if rehearsal.exec_status == STOPPED_PHASE:
            return REPLAY_PHASE

        raise RuntimeError("Unknown exec_status")

# ------------------------------------------------------------
# prepare_resume
# ------------------------------------------------------------

def prepare_resume(rehearsal: Rehearsal):
    rehearsal.exec_status = REPLAY_PHASE

    # 1. 切 resume 視野
    if rehearsal.resume_from_event_id:
        resume_from_index = None
        for i, ev in enumerate(rehearsal.event_log):
            if ev.get("id") == rehearsal.resume_from_event_id and ev.get("kind") == "before_ini_child":
                stop_event_id = ev.get("id")
                has_after = any(
                    e for e in rehearsal.event_log
                    if e.get("kind") == "after_decision" and e.get("id") == stop_event_id
                )
                if has_after:
                    resume_from_index = i
                    break

        if resume_from_index is not None:
            rehearsal.event_log_resume = rehearsal.event_log[:resume_from_index+1]

    if not rehearsal.event_log_resume:
        rehearsal.event_log_resume = rehearsal.event_log.copy()

    # 2. 找 unpaired events
    unpaired = set()
    for ev in rehearsal.event_log_resume:
        if ev.get("kind") == "before_ini_child":
            unpaired.add(ev["id"])
        elif ev.get("kind") == "after_decision":
            if ev["id"] in unpaired:
                unpaired.remove(ev["id"])

    rehearsal.unpaired_event_ids = list(unpaired)