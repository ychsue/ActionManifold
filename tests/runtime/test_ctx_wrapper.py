# test_ctx_wrapper.py

from am_core.ctx.context import Ctx
from am_core.ctx.ctx_wrapper import WrappedCtx, CtxDeltaCollector

def test_sm_set_does_not_modify_real_ctx():
    real = Ctx()
    real.set("a", 1)

    delta = CtxDeltaCollector()
    wrapped = WrappedCtx(real, delta)

    wrapped.set("a", 2)

    # 真 ctx 不應該被改
    assert real.get("a") == 1
    # delta 裡應該有一筆 local 寫入
    assert delta.ops == [{"mode": "local", "key": "a", "to": 2}]
    # wrapped_ctx 讀取時會看到 delta 的寫入
    assert wrapped.get("a") == 2


def test_apply_delta_modifies_real_ctx():
    real = Ctx()
    real.set("a", 1)

    writes = [{"mode": "local", "key": "a", "to": 2}]
    real.apply_writes(writes)

    assert real.get("a") == 2


def test_set_root_updates_root_scope():
    root = Ctx()
    root.set("x", 0)
    child = root.child()

    delta = CtxDeltaCollector()
    wrapped = WrappedCtx(child, delta)

    wrapped.set_root("x", 10)
    assert root.get("x") == 0  # 真 ctx 不應該被改
    child.apply_writes(delta.ops)
    # apply 後 root 的 x 才會變成 10
    assert root.get("x") == 10


def test_sm2_can_read_sm1_update():
    root = Ctx()
    root.set("x", 0)
    child = root.child()

    # SM1
    d1 = CtxDeltaCollector()
    w1 = WrappedCtx(child, d1)
    w1.set_root("x", 10)
    child.apply_writes(d1.ops)

    # SM2
    d2 = CtxDeltaCollector()
    w2 = WrappedCtx(child, d2)
    assert w2.get("x") == 10