# src/am_core/world.py

from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Any, Dict, Optional

from .ctx.context import Ctx
from .orchestrator import Orchestrator
from .playbook import Playbook


class World:
    """
    World = Orchestrator 的容器 + 全域資源管理者。
    - 管理全域 metadata
    - 管理全域 ctx
    - 提供統一的 run / simulate / replay / resume API
    """

    def __init__(
        self,
        playbook: Playbook,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        ctx: Optional[Ctx] = None,
        name: str = "world",
    ):
        self.playbook = playbook
        self.metadata = metadata or {}
        self.ctx = ctx or Ctx(parent=None,current_state= playbook.initial_state())
        self.name = name

        # 建立 root orchestrator
        self.root = Orchestrator(
            playbook=self.playbook,
            ctx=self.ctx,
            metadata=self.metadata,
            name=name,
        )
        
        # event subscribers，給 GUI/CLI/ VSCode Extension 用
        self._subscribers = set()
        
        # runtime flags
        self._task = None  # asyncio.Task for the main execution, used for cancellation, status check, etc.
        self._running = False

    #-------------------------
    # Runtime 控制：start/run/simulate/replay/resume
    #-------------------------
       
    def start(self, sm_mode="normal"):
        '''
        啟動 World 的執行，非阻塞。
         - sm_mode: state machine 的執行模式，預設為 "normal"，也可以是 "interactive_simulate"（互動式模擬），"replay"（重播）或 "resume"（從特定事件繼續）。
        '''
        if self._running:
            return  # already running
        self._running = True
        self._task = asyncio.create_task(self._run_loop(sm_mode))

    async def run(self, sm_mode="normal"):
        """
        阻塞執行，直到完成。
        """
        self._running = True
        return await self._run_loop(sm_mode)
    
    async def _run_loop(self, sm_mode):
        try:
            result = await self.root.run(sm_mode=sm_mode)
            return result
        finally:
            self._running = False
            self._task = None

    async def simulate(self):
        return await self.root.run(sm_mode="interactive_simulate")

    async def replay(self):
        rehearsal = self.ctx.get("rehearsal")
        rehearsal.mode = "replay"
        return await self.root.run(sm_mode="normal")

    async def resume(self, event_id: str):
        rehearsal = self.ctx.get("rehearsal")
        rehearsal.mode = "resume"
        rehearsal.resume_from_event_id = event_id
        return await self.root.run(sm_mode="normal")

    #--------------------------------------------
    # event subscription
    #--------------------------------------------
    def subscribe(self, callback):
        """
        訂閱事件，callback 會在每次事件發生時被呼叫，參數為事件資料。
        """
        self._subscribers.add(callback)
    
    def unsubscribe(self, callback):
        """
        取消訂閱事件。
        """
        self._subscribers.discard(callback)

    #------------------------------------------------------------
    # emit，可能是 SSE/WebSocket 的事件來源
    #------------------------------------------------------------
    def emit(self, event):
        """
        發出事件，會呼叫所有訂閱者的 callback。
        """
        for callback in self._subscribers:
            callback(event)

    #------------------------------------------------------------
    # 狀態查詢 API
    #------------------------------------------------------------
    def get_event_log(self):
        """
        取得事件日誌，包含所有發生過的事件。
        """
        return list(self.root.events)

    # ------------------------------------------------------------
    # GUI entrypoint（未來用）
    # ------------------------------------------------------------
    # TODO：看來得想辦法傳目前 ctx 與 metadata 上來，讓 GUI 可以 render 出來
    def get_runtime_state(self):
        """
        給 GUI 用：取得目前 world 的 metadata / ctx / events。
        """
        # 取得最後一個event 的 kind 為 before_sm_execute 的 event，裡面應該包含了最新的 ctx 與 metadata
        before_sm_execs = [e for e in reversed(self.root.events) if e.get("kind") == "before_sm_execute"]
        last = before_sm_execs[0] if before_sm_execs else None
        events = self.get_event_log()

        if last is None:
            # 沒有 before_sm_execute 的事件，可能是還沒開始執行，或是 playbook 沒有 state machine
            return {
                "current_state": None,
                "kind": None,
                "chain": None,
                "ctx": None,
                "ctx_delta": None,
                "metadata": self.metadata,
                "metadata_delta": None,
                "status": "not_started",
                "events": events,
            }

        return {
            "current_state": last.get("state"),
            "kind": last.get("kind"),
            "chain": last.get("chain"),
            "ctx": last.get("ctx"),  # from before_sm_execute
            "ctx_delta": last.get("ctx_delta"),  # from after_sm_execute
            "metadata": last.get("metadata"),
            "metadata_delta": last.get("metadata_delta"),
            "status": last.get("status"),
            "events": events,
        }

    def describe_project(self):
        """
        給 GUI 用：描述目前的 playbook 結構，包含 state machine、states、actions 等等。
        """
        return self._walk_playbook(self.playbook,["root"])
        
    def _walk_playbook(self, playbook: Playbook, path: list[str]):
        node = {
            "path": path,
            "file": playbook.base_path,
            "states": {},
            "subflows": [],
        }
        for state_name, state_def in playbook.states.items():
            node["states"][state_name] = {
                "class_": state_def.get("class_"),
                "subflow": isinstance(state_def.get("subflow"), dict) or isinstance(state_def.get("subflow"), str),
            }
            
            sub = state_def.get("subflow")
            if isinstance(sub, dict):
                buf = Playbook(sub, base_path=playbook.base_path)
                node["subflows"].append(self._walk_playbook(buf, path + [state_name]))
            elif isinstance(sub, str) and sub.startswith("playbook:") and playbook.base_path is not None:
                rel_path = sub.split(":", 1)[1]
                pb_path = Path(playbook.base_path) / rel_path
                pb_data = playbook.load_from_file(str(pb_path)).data
                buf = Playbook(pb_data, base_path=str(pb_path.parent))
                node["subflows"].append(self._walk_playbook(buf, path + [state_name]))
                
        return node


#------------------------------------------------------------
# ctx/metadata reconstruct API（未來用）
#------------------------------------------------------------
def reconstruct_ctx_tree(events: list[Dict[str, Any]]):
    tree = {}
    for ev in events:
        if ev["kind"] == "after_sm_execute":
            state = ev["state"]
            delta = ev.get("ctx_delta", [])
            if state not in tree:
                tree[state] = {}
            for op in delta:
                key = op["key"]
                if op["mode"] == "set":
                    tree[state][key] = op["value"]
                elif op["mode"] == "del":
                    tree[state].pop(key, None)
    return tree 