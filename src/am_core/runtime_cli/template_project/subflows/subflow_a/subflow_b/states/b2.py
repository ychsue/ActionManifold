from am_core.state_machine import StateMachine

class A2(StateMachine):
    async def predict_output(self):
        return {"status": "ok", "msg": "b2 done"}