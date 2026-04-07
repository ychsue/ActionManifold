from am_core.state_machine import StateMachine

class A1(StateMachine):
    async def predict_output(self):
        return {"status": "ok", "msg": "b1 done"}