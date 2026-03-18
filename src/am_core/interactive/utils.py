# am_core/interactive/utils.py
import re
from typing import List, Dict, Any


def merge_ctx_delta_with_validation(
    original: List[Dict[str, Any]],
    patch: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge ctx_delta patch into original ctx_delta.
    Only allow modifying existing (mode, key) pairs.
    Do NOT allow creating new keys.
    """

    # 建立查詢表 {(mode, key): index}
    index = {(entry["mode"], entry["key"]): i for i, entry in enumerate(original)}

    merged = list(original)

    for p in patch:
        mk = (p["mode"], p["key"])
        if mk not in index:
            raise ValueError(f"ctx_delta patch contains unknown (mode,key): {mk}")

        i = index[mk]
        merged[i] = p  # replace entire entry

    return merged

def merge_dict_with_validation(
    field_name: str,
    original: Dict[str, Any],
    patch: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge Dict patch into original Dict.
    Only allow modifying existing keys.
    """
    merged = dict(original)

    for k, v in patch.items():
        if k not in original:
            raise ValueError(f"{field_name} patch contains unknown key: {k}")
        merged[k] = v

    return merged

def regexp_d_get(d: Dict[str, Any], k: str, default: Any = None) -> Any:
    """
    d 的 key 有可能是 regexp str, k 為實際的字串，這個 function 會幫你找出 d 裡面 key 的 regexp 能 match k 的那一個，然後回傳對應的 value。
    """
    for key, value in d.items():
        if re.fullmatch(key, k):
            return value
    return default

def regexp_k_get(d: Dict[str, Any], k: str, default: Any = None) -> Any:
    """
    d 為要被搜尋的字典, k 為regexp字串，這個 function 會幫你找出 d 裡面 key 能 match k 的那一個，然後回傳對應的 value。
    """
    for key, value in d.items():
        if re.fullmatch(k, key):
            return value
    return default
