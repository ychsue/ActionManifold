from am_core.state_machine import StateMachine

class Step1(StateMachine):
    async def predict_output(self):
        return {"status": "ok", "msg": "step1 done"}