# metadata_wrapper.py

from typing import Any

from anyio import value


class MetadataDeltaCollector:
    def __init__(self):
        self.ops: dict[str, Any] = {}

    def set(self, key: str, value: Any) -> None:
        self.ops[key] = value

    def clear(self):
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

    def get(self, key: str, default=None):
        if key in self._delta.ops:
            value = self._delta.ops[key]
            if value is None:
                return default
            return value
        return self._real.get(key, default)

    def set(self, key: str, value: Any):
        self._delta.set(key, value)