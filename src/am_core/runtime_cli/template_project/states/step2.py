from am_core.state_machine import StateMachine

class Step2(StateMachine):
    async def predict_output(self):
        return {"status": "ok", "msg": "step2 done"}