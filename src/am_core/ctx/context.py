# src/am_core/context.py

from __future__ import annotations
from typing import Any, Dict, List, Optional


class Ctx:
    """
    Lexical-scope context tree with write-log semantics.

    語意：
    - ctx 是一棵 lexical scope tree（形狀 immutable）
    - child_ctx = parent_ctx.child(...) 會產生新的 ctx，不會修改 parent
    - set_local / set_nearest / set_root 會記錄 write log（_writes）
    - dump_writes() 會輸出所有寫入意圖（取代 diff）
    - apply_writes() 會根據 write log patch 整棵 ctx tree（child + parent）
    - replay/resume 時可重建 child_ctx 的 ephemeral 狀態
    """

    __slots__ = ("_parent", "_values", "_writes")

    def __init__(self, parent: Optional["Ctx"] = None, **values: Any):
        self._parent = parent
        self._values = {"current_state": "Root",} if parent is None else values
        self._writes: List[Dict[str, Any]] = []   # write log

    # -------------------------
    # 查找（向上 lexical lookup）
    # -------------------------
    def get(self, key: str, default: Any = None) -> Any:
        if key in self._values:
            return self._values[key]
        if self._parent:
            return self._parent.get(key, default)
        return default

    # -------------------------
    # 設定（只設定當前層，不修改 parent）
    # set_local（原本的 set）
    # -------------------------
    def set(self, key: str, value: Any) -> None:
        """只寫當前層，並記錄 write log"""
        self._values[key] = value
        self._writes.append({
            "mode": "local",
            "key": key,
            "to": value,
        })

    # -------------------------
    # set_nearest：往上找第一個擁有 key 的 ctx
    # -------------------------
    def set_nearest(self, key: str, value: Any) -> None:
        ctx = self._find_nearest_ctx_with_key(key)
        if ctx is None:
            # fallback：寫到 root
            self.set_root(key, value)
            return

        ctx._values[key] = value
        self._writes.append({
            "mode": "nearest",
            "key": key,
            "to": value,
        })

    def _find_nearest_ctx_with_key(self, key: str) -> Optional["Ctx"]:
        ctx = self
        while ctx:
            if key in ctx._values:
                return ctx
            ctx = ctx._parent
        return None

    # -------------------------
    # set_root：寫到 root ctx
    # -------------------------
    def set_root(self, key: str, value: Any) -> None:
        root = self._find_root()
        root._values[key] = value
        self._writes.append({
            "mode": "root",
            "key": key,
            "to": value,
        })

    def _find_root(self) -> "Ctx":
        ctx = self
        while ctx._parent:
            ctx = ctx._parent
        return ctx

    # -------------------------
    # 建立 child ctx（ephemeral）
    # -------------------------
    def child(self, **overrides: Any) -> "Ctx":
        """
        建立新的 child ctx，不會修改 parent。
        """
        return Ctx(parent=self, **overrides)

    # -------------------------
    # dump_writes（取代 diff）
    # -------------------------
    def dump_writes(self) -> List[Dict[str, Any]]:
        """輸出所有寫入意圖"""
        return list(self._writes)

    # -------------------------
    # apply_writes（取代 apply_delta）
    # -------------------------
    def apply_writes(self, writes: List[Dict[str, Any]], into_writes: bool = False) -> None:
        """
        根據 write log patch 整棵 ctx tree。
        - local：寫當前層
        - nearest：往上找第一個擁有 key 的 ctx
        - root：寫 root
        """
        for w in writes:
            if into_writes:
                self._writes.append(w)
            mode = w["mode"]
            key = w["key"]
            value = w["to"]

            if mode == "local":
                self._values[key] = value

            elif mode == "nearest":
                ctx = self._find_nearest_ctx_with_key(key)
                if ctx:
                    ctx._values[key] = value
                else:
                    self._find_root()._values[key] = value

            elif mode == "root":
                self._find_root()._values[key] = value

            else:
                raise ValueError(f"Unknown write mode: {mode}")

    # -------------------------
    # debug
    # -------------------------
    def flatten(self) -> Dict[str, Any]:
        result = {}
        if self._parent:
            result.update(self._parent.flatten())
        result.update(self._values)
        return result

    def __repr__(self) -> str:
        return f"Ctx(values={self._values}, writes={self._writes}, parent={bool(self._parent)})"