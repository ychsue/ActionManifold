# src/am_core/runtime_store.py

from typing import Dict, Any
import abc

class RuntimeStore(abc.ABC):
    """
    給 Orchestrator / StateMachine 使用的 runtime-only store。
    不可序列化、不進入 ctx、不進入 event_log、不進入 replay/resume。
    """

    @abc.abstractmethod
    def register_orchestrator(self, orch) -> None:
        ...

    @abc.abstractmethod
    def unregister_orchestrator(self, orch_id: str) -> None:
        ...

    @abc.abstractmethod
    def register_pending(self, orch_id: str, future) -> None:
        ...

    @abc.abstractmethod
    def unregister_pending(self, orch_id: str) -> None:
        ...

    @abc.abstractmethod
    def resolve_pending(self, orch_id: str, decision: Any) -> None:
        ...

    @abc.abstractmethod
    def get_active_orchestrators(self) -> Dict[str, Any]:
        ...

    @abc.abstractmethod
    def get_pending(self) -> Dict[str, Any]:
        ...

from typing import Dict, Any

class WorldRuntimeStore(RuntimeStore):
    def __init__(self):
        # 不可序列化、不可 replay 的 runtime-only store
        self.active_orchestrators: Dict[str, Any] = {}
        self.pending_decisions: Dict[str, Any] = {}
        self.buffered_decisions: Dict[str, Any] = {}

    def register_orchestrator(self, orch) -> None:
        self.active_orchestrators[orch.orch_id] = orch

    def unregister_orchestrator(self, orch_id: str) -> None:
        self.active_orchestrators.pop(orch_id, None)

    def unregister_pending(self, orch_id: str) -> None:
        self.pending_decisions.pop(orch_id, None)

    def register_pending(self, orch_id: str, future):
        # 如果之前就有 decision 先到了，這裡直接用
        if orch_id in self.buffered_decisions:
            decision = self.buffered_decisions.pop(orch_id)
            future.set_result(decision)
        else:
            self.pending_decisions[orch_id] = future

    def resolve_pending(self, orch_id: str, decision: Any) -> None:
        fut = self.pending_decisions.get(orch_id)
        if fut and not fut.done():
            fut.set_result(decision)
            self.pending_decisions.pop(orch_id, None)
        else:
            # 還沒有 pending，就先記起來
            self.buffered_decisions[orch_id] = decision

    def get_active_orchestrators(self) -> Dict[str, Any]:
        return dict(self.active_orchestrators)

    def get_pending(self) -> Dict[str, Any]:
        return dict(self.pending_decisions)
