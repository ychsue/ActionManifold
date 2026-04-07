from am_core.state_machine import StateMachine

class A2(StateMachine):
    async def predict_output(self):
        return {"status": "ok", "msg": "a2 done"}