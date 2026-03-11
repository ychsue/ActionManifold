# tests/example_sm.py
from typing import List
from am_core.state_machine import StateMachine
from .example_schema import MyOutputSchema, CtxWrite, MyMetadataSchema

class ExampleSM(StateMachine[MyOutputSchema, CtxWrite, MyMetadataSchema]):
    async def predict_output(self) -> MyOutputSchema:
        return {"status": "ok", "result": 7}

    async def predict_ctx_delta(self) -> List[CtxWrite]:
        return [{"mode": "nearest", "key": "x", "to": 7}]

    async def predict_metadata_delta(self) -> MyMetadataSchema:
        return {"attempt": 1}

    async def _run(self, wrapped_metadata) -> MyOutputSchema:
        # real side effect path — must return same shape as predict_output
        self.wrapped_ctx.set_nearest("x", 7)
        wrapped_metadata.set("attempt", 1)
        return {"status": "ok", "result": 7}