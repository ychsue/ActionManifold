# metadata_wrapper.py

from typing import Any

from anyio import value


class MetadataDeltaCollector:
    def __init__(self):
        self.ops: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self.ops[key] = value

    def clear(self) -> None:
        self.ops.clear()


class WrappedMetadata:
    """
    SM 看到的 metadata：
    - get → 真 metadata
    - set → 記錄 delta，不改真 metadata
    """

    def __init__(self, real_metadata: dict, delta: MetadataDeltaCollector):
        self._real = real_metadata
        self._delta = delta

    # 輸出的 type 若 default 非 None 時，就是 default 的 type；若 default 是 None，則輸出 Any
    def get(self, key: str, default: Any = None) -> Any:
        if key in self._delta.ops:
            value = self._delta.ops[key]
            if value is None:
                return default
            return value
        return self._real.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._delta.set(key, value)