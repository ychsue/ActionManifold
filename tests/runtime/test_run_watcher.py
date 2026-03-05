# tests/runtime/test_run_watcher.py

import time
from am_core.run_watcher import run_watcher


def test_pass_through_ok():
    """
    SM 回傳 ok，沒有 timeout，也沒有 retry_times。
    run_watcher 應該 pass-through 並產生 event。
    """
    state_def = {"name": "NextState"}
    metadata = {"retries": {}}

    sm_output = {"status": "ok"}

    enriched = run_watcher(
        state_name="NextState",
        state_def=state_def,
        sm_output=sm_output,
        metadata=metadata,
    )

    assert enriched["status"] == "ok"
    assert "event" in enriched
    event = enriched["event"]

    assert event["state"] == "NextState"
    assert event["output"] == sm_output
    assert event["retry_count"] == 0
    assert event["timeout"] is False


def test_timeout_detected_by_duration():
    """
    state_def 有 timeout=0.01 秒，SM 執行時間超過。
    run_watcher 應該回傳 status=timeout。
    """
    state_def = {"name": "NextState", "timeout": 0.01}
    metadata = {"retries": {}}

    sm_output = {"status": "ok"}

    # 模擬 SM 執行時間
    start = time.time()
    time.sleep(0.02)
    end = time.time()

    enriched = run_watcher(
        state_name="NextState",
        state_def=state_def,
        sm_output=sm_output,
        metadata=metadata,
        start_time=start,
        end_time=end,
    )

    assert enriched["status"] == "timeout"
    event = enriched["event"]
    assert event["timeout"] is True
    assert event["retry_count"] == 0


def test_timeout_flag_override():
    """
    若 orchestrator 傳入 timeout_flag=True，
    run_watcher 必須直接視為 timeout，不看時間。
    """
    state_def = {"name": "NextState", "timeout": 999}
    metadata = {"retries": {}}

    sm_output = {"status": "ok"}

    enriched = run_watcher(
        state_name="NextState",
        state_def=state_def,
        sm_output=sm_output,
        metadata=metadata,
        timeout_flag=True,
    )

    assert enriched["status"] == "timeout"
    assert enriched["event"]["timeout"] is True


def test_retry_logic():
    """
    retry_times=3，已 retry 1 次 → fail → 應該 retry。
    """
    state_def = {"name": "NextState", "retry_times": 3}
    metadata = {"retries": {"NextState": 1}}

    sm_output = {"status": "fail"}

    enriched = run_watcher(
        state_name="NextState",
        state_def=state_def,
        sm_output=sm_output,
        metadata=metadata,
    )

    assert enriched["status"] == "retry"
    event = enriched["event"]

    assert event["retry_count"] == 2
    assert metadata["retries"]["NextState"] == 2  # metadata 必須更新


def test_retry_exhausted():
    """
    retry_times=3，已 retry 3 次 → fail → 不可 retry → status=fail。
    """
    state_def = {"name": "NextState", "retry_times": 3}
    metadata = {"retries": {"NextState": 3}}

    sm_output = {"status": "fail"}

    enriched = run_watcher(
        state_name="NextState",
        state_def=state_def,
        sm_output=sm_output,
        metadata=metadata,
    )

    assert enriched["status"] == "fail"
    event = enriched["event"]

    assert event["retry_count"] == 3
    assert metadata["retries"]["NextState"] == 3  # 不應增加


def test_metadata_delta_is_recorded():
    """
    若 retry_count 有變化，metadata_delta 應記錄變化。
    """
    state_def = {"name": "NextState", "retry_times": 5}
    metadata = {"retries": {"NextState": 0}}

    sm_output = {"status": "fail"}

    enriched = run_watcher(
        state_name="NextState",
        state_def=state_def,
        sm_output=sm_output,
        metadata=metadata,
    )

    event = enriched["event"]
    assert event["metadata_delta"] == {"retries": {"NextState": 1}}