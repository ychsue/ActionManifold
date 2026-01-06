from ast import Or
import json
from pathlib import Path
from typing import Any, Optional
import weakref
import types
import inspect

from sympy import Function

from .leak_monitor import LeakMonitor

class CtxBus:
    """
    CtxBus 是一個簡單的事件總線，用於在不同的 StateMachine 之間傳遞事件。像是公佈欄一樣，任何訂閱了 CtxBus 的 StateMachine 都能接收到發佈的事件。
    這樣的設計有助於解耦不同 StateMachine 之間的依賴關係，讓它們能夠更靈活地互動。
    例如，一個 StateMachine 可以在完成某個任務後發佈一個事件，其他訂閱了該事件的 StateMachine 就能夠根據這個事件來決定自己的行為。
    這種事件驅動的架構有助於提升系統的可擴展性和維護性。
    """
    def __init__(self):
        self.channels = {}  # name -> list of subscribers
        self.store = {}

    def subscribe(self, fn: Function|types.MethodType, channel: str = "default"):
        subs = self.channels.setdefault(channel, [])

        # bound method → WeakMethod
        if inspect.ismethod(fn):
            subs.append(weakref.WeakMethod(fn))
            return

        # function → weakref.ref
        try:
            subs.append(weakref.ref(fn))
            return
        except TypeError:
            # lambda / builtins → cannot weakref
            subs.append(fn)

    def publish(self, event, channel: str = "default"):
        subs = self.channels.get(channel, [])
        alive = []

        for sub in subs:
            if isinstance(sub, weakref.ReferenceType):
                fn = sub()
                if fn:
                    fn(event)
                    alive.append(sub)
            else:
                sub(event)
                alive.append(sub)

        self.channels[channel] = alive

    def set(self, key: str, value: Any):
        self.store[key] = value

    def get(self, key: str, default: Optional[Any]=None):
        return self.store.get(key, default)
        
class WorldCtx:
    """
    World 主要是為了紀錄整個 workflow 的執行狀態，方便事後追蹤與除錯。
    """
    def __init__(self, workflow_id: str, run_id: str, run_dir: Path):
        self.workflow_id = workflow_id
        self.run_id = run_id
        self.run_dir = run_dir
        self.state = {}
        self.event_log = []

    def log_event(self, event):
        self.event_log.append(event)

    def dump(self):
        path = self.run_dir / f"world_{self.run_id}.json"
        data = {
            "workflow_id": self.workflow_id,
            "run_id": self.run_id,
            "state": self.state,
            "event_log": self.event_log,
        }
        stJson = json.dumps(data, indent=2, ensure_ascii=False)
        
        # write to file even if run_dir does not exist
        self.run_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(stJson, encoding="utf-8" )

    @staticmethod
    def load(run_dir, run_id: str = "world"):
        data = json.loads((run_dir / f"world_{run_id}.json").read_text())
        wc = WorldCtx(data["workflow_id"], data["run_id"], run_dir)
        wc.state.update(data["state"])
        wc.event_log.extend(data["event_log"])
        return wc
    
class BaseCtx:
    """
    BaseCtx 是 Orchestrator 和 StateMachine 的共同父類別，提供基本的上下文功能。
    """
    def __init__(self, name, parent_orchCtx: Optional["OrchCtx"]=None):
        LeakMonitor.track_ctx(self)
        self.name = name
        self.parent = parent_orchCtx
        self.exposure = {}
        self.init = {}
        self.scratch = {}
        self.event = {}
        self.ref = {}

    def get(self, key, default: Optional[Any]=None):
        if key in self.exposure:
            return self.exposure[key]
        if self.parent:
            return self.parent.get(key, default)
        return default

    def get_ref(self, key, default: Optional[Any]=None):
        if key in self.ref:
            return self.ref[key]
        if self.parent:
            return self.parent.get_ref(key, default)
        return default

    def set(self, key, value:Any):
        self.exposure[key] = value
        
    def set_ref(self, key, value:Any):
        self.ref[key] = value

    def print_ctx_tree(self, indent=0):
        print("  " * indent + self.name)
        for child in getattr(self, "children", []):
            child.print_ctx_tree(indent + 1)
class OrchCtx(BaseCtx):
    """
    Orchestrator 就像檔案系統中的目錄，所以，其parent是另一個OrchCtx(目錄)。
    """
    def __init__(self, name, parent_orchCtx: Optional["OrchCtx"]=None):
        super().__init__(name, parent_orchCtx)
        self.children: list[BaseCtx] = []
        
    def add_child(self, child_ctx: BaseCtx):
        self.children.append(child_ctx)
        
class StateCtx(BaseCtx):
    """
    State 就像檔案系統中的檔案，所以，其parent是OrchCtx(目錄)。
    """
    def __init__(self, name, parent_orchCtx: Optional["OrchCtx"]=None):
        super().__init__(name, parent_orchCtx)