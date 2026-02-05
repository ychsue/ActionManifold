# src/am_core/context.py

from __future__ import annotations
from typing import Any, Dict, Optional


class Ctx:
    """
    Immutable lexical-scope context tree.

    語意：
    - ctx 是一棵不可變的語意樹（lexical scope）
    - child_ctx = parent_ctx.child(...) 會產生新的 ctx，不會修改 parent
    - child_ctx 只有單向指向 parent，不會形成 cycle
    - lookup 是向上查找（shadowing）
    - 適合 SM / ORCH / WORLD 的嵌套
    - replay/resume 時可重建 ctx_tree
    """

    __slots__ = ("_parent", "_values")

    def __init__(self, parent: Optional["Ctx"] = None, **values: Any):
        self._parent = parent
        self._values = values

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
    # 是否存在（向上 lexical lookup）
    # -------------------------
    def has(self, key: str) -> bool:
        if key in self._values:
            return True
        if self._parent:
            return self._parent.has(key)
        return False

    # -------------------------
    # 建立子 ctx（shadow override）
    # -------------------------
    def child(self, **overrides: Any) -> "Ctx":
        """
        建立新的 child ctx，不會修改 parent。
        """
        return Ctx(parent=self, **overrides)

    # -------------------------
    # 將 ctx 展開成 dict（用於 debug 或 replay）
    # -------------------------
    def flatten(self) -> Dict[str, Any]:
        """
        將整個 lexical scope 展開成一個 dict。
        子層覆蓋父層。
        """
        result = {}
        if self._parent:
            result.update(self._parent.flatten())
        result.update(self._values)
        return result

    # -------------------------
    # 方便 debug
    # -------------------------
    def __repr__(self) -> str:
        return f"Ctx(values={self._values}, parent={bool(self._parent)})"