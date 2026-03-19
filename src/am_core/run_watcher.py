# src/am_core/run_watcher.py

from __future__ import annotations

import time
from typing import Any, Dict, Optional


def run_watcher(
    *,
    state_name: str,
    state_def: Dict[str, Any],
    sm_output: Dict[str, Any],
    metadata: Dict[str, Any],
    start_time: Optional[float] = None,
    end_time: Optional[float] = None,
    timeout_flag: Optional[bool] = None,
    parent_state: Optional[str] = None,
) -> Dict[str, Any]:
    """
    監控單一 state 的執行結果，決定語意上的 status，並產生 event。

    語意：
    - 基本輸入：state_name, state_def, sm_output, metadata
    - timeout：
        - 若 timeout_flag 明確給定 → 直接使用
        - 否則若 state_def 有 "timeout" 且 end_time - start_time 超過 → 視為 timeout
    - retry：
        - 若 sm_output["status"] == "fail" 且 retry_count < retry_times → status="retry"
        - 若 retry_count >= retry_times → status="fail"
    - event：
        - state, output, enriched, retry_count, timeout, metadata_delta, start_time, end_time, parent_state
    """

    # --- 時間處理 ---

    if start_time is None:
        start_time = time.time()
    if end_time is None:
        end_time = time.time()

    # --- 取得原始 status ---

    status = sm_output.get("status", "ok")

    # --- timeout 判斷 ---

    timeout_occurred = False

    if timeout_flag is not None:
        timeout_occurred = timeout_flag
    else:
        timeout_setting = state_def.get("timeout")
        if timeout_setting is not None:
            duration = end_time - start_time
            if duration > float(timeout_setting):
                timeout_occurred = True

    if timeout_occurred:
        status = "timeout"

    # --- retry 判斷 ---

    retries_meta = metadata.setdefault("retries", {})
    current_retry = int(retries_meta.get(state_name, 0))
    retry_times = state_def.get("retry_times")

    metadata_delta: Dict[str, Any] = {}

    if status == "fail" and retry_times is not None:
        if current_retry < int(retry_times):
            # 還可以 retry
            current_retry += 1
            retries_meta[state_name] = current_retry
            metadata_delta = {"retries": {state_name: current_retry}}
            status = "retry"
        else:
            # retry 已用完，維持 fail
            pass

    # 如果是 SM，就要再把 sm_output 裡面的 metadata_delta 也合併進來，
    if sm_output.get("is_SM") and sm_output.get("metadata_delta"):
        buf = dict(sm_output["metadata_delta"])
        buf.update(metadata_delta)  # 以 run_watcher 的 metadata_delta 為主，因為它是根據原本的 metadata 加上 SM 修改後的 metadata_delta 計算出來的
        metadata_delta = buf

    # --- event 結構 ---

    event: Dict[str, Any] = {
        "state": state_name,
        "parent_state": parent_state,
        "output": sm_output,
        "enriched_status": status,
        "retry_count": current_retry,
        "timeout": timeout_occurred,
        "metadata_delta": metadata_delta,
        "start_time": start_time,
        "end_time": end_time,
    }

    enriched_output: Dict[str, Any] = {
        "status": status,
        "event": event,
    }

    return enriched_output