# tests/test_generic_compat.py

from typing import Any, TypedDict
import pytest
from typing_extensions import NotRequired
from am_core.ctx.context import Ctx
from am_core.ctx.ctx_wrapper import CtxDeltaCollector, WrappedCtx
from am_core.state_machine import StateMachine

class MySchema(TypedDict):
    status: str
    value: NotRequired[int]

class SM1(StateMachine):  # 不使用泛型
    async def predict_output(self):
        return {"status": "ok"}

class SM2(StateMachine[MySchema, Any, Any]):  # 使用泛型
    async def predict_output(self) -> MySchema:
        return {"status": "ok", "value": 42}

@pytest.mark.asyncio
async def test_generic_backward_compat():
    wctx = WrappedCtx(Ctx(), CtxDeltaCollector())
    sm1 = SM1(wctx)
    sm2 = SM2(wctx)

    # 不會噴錯
    assert isinstance(sm1, StateMachine)
    assert isinstance(sm2, StateMachine)

    # output 型別正確
    assert (await sm1.predict_output()).__class__ == dict
    assert (await sm2.predict_output()).__class__ == dict  # TypedDict 也是 dict