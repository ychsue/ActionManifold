# src/am_core/builtin_states.py

from __future__ import annotations
from typing import Any, Dict

from am_core.ctx.metadata_wrapper import WrappedMetadata

from .state_machine import StateMachine


class SuccessStateMachine(StateMachine):
    """
    成功終止節點。
    語意：
    - 永遠回傳 status="ok"
    - 不修改 metadata
    """
    async def _run(self, wrapped_metadata: WrappedMetadata) -> Dict[str, Any]:
        self.emit({
            "type": "sm",
            "state": "Success",
            "status": "ok",
        })
        return {"status": "ok"}


class ErrorStateMachine(StateMachine):
    """
    失敗終止節點。
    語意：
    - 永遠回傳 status="fail"
    - 不修改 metadata
    """
    async def _run(self, wrapped_metadata: WrappedMetadata) -> Dict[str, Any]:
        self.emit({
            "type": "sm",
            "state": "Error",
            "status": "fail",
        })
        return {"status": "fail"}


class FailStateMachine(StateMachine):
    """
    與 Error 類似，但語意上可區分：
    - Error：系統錯誤、例外、timeout
    - Fail：邏輯失敗（例如驗證不通過）
    """
    async def _run(self, wrapped_metadata: WrappedMetadata) -> Dict[str, Any]:
        self.emit({
            "type": "sm",
            "state": "Fail",
            "status": "fail",
        })
        return {"status": "fail"}