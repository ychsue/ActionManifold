# ctx_wrapper.py

from typing import Any

from .context import Ctx


class CtxDeltaCollector:
    def __init__(self):
        # list[dict]，格式跟 Ctx._writes 一樣
        self.ops: list[dict[str, Any]] = []

    def add_nearest(self, key: str, value: Any) -> None:
        self.ops.append({
            "mode": "nearest",
            "key": key,
            "to": value,
        })

    def add_root(self, key: str, value: Any) -> None:
        self.ops.append({
            "mode": "root",
            "key": key,
            "to": value,
        })

    def add(self, key: str, value: Any) -> None:
        self.ops.append({
            "mode": "local",
            "key": key,
            "to": value,
        })

    def clear(self) -> None:
        self.ops.clear()


class WrappedCtx:
    """
    SM 看到的 ctx：
    - get → 真 ctx
    - set → 記錄 delta，不改 ctx
    """

    def __init__(self, real_ctx: Ctx, delta_collector: CtxDeltaCollector):
        self._real = real_ctx
        self._delta = delta_collector

    # --- 讀取永遠是真 ctx ---
    def get(self, key:str, default: Any =None) -> Any:
        # 多加先確定 key 在 delta 裡沒有被 set 過，才從 real ctx 讀取
        for op in reversed(self._delta.ops):
            if op["key"] == key:
                return op["to"]
        return self._real.get(key, default)

    # --- 寫入永遠記錄 delta，不改 ctx ---
    def set_nearest(self, key: str, value: Any) -> None:
        self._delta.add_nearest(key, value)

    def set_root(self, key: str, value: Any) -> None:
        self._delta.add_root(key, value)

    def set(self, key: str, value: Any) -> None:
        self._delta.add(key, value)