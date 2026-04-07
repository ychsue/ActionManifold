import asyncio
from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine


class FailTwice(StateMachine):
    async def predict_output(self):
        return {"status": "ok", "state": self.name}
    
    def _ui_hint(self):
        return {
            "status": ["ok", "fail"]
        }

    async def _run(self, wrapped_metadata):
        retries = wrapped_metadata.get("retries", {}).get(self.name, 0)

        if retries < 2:
            print(f"[{self.name}] failing (retry {retries})")
            return {"status": "fail", "state": self.name}
        else:
            print(f"[{self.name}] success after retries")
            return {"status": "ok", "state": self.name}


class Success(StateMachine):
    async def predict_output(self):
        return {"status": "ok", "state": self.name}

    async def _run(self, wrapped_metadata):
        print(f"[{self.name}] success")
        return {"status": "ok", "state": self.name}


def make_playbook():
    return Playbook({
        "states": [
            {"name": "A", "to": "B"},
            {"name": "B", 
             "switch":{
                "ok": "C",
                "retry": "A"
                }, 
             "retry_times": 2
            },
            {"name": "C", "to": None},
        ],
        "initial": "A",
        "registry": {
            "A": Success,
            "B": FailTwice,
            "C": Success,
        }
    })


async def main():
    ctx = Ctx()
    orch = Orchestrator(make_playbook(), ctx)
    # 直接跑
    # result = await orch.run()
    # Interactive 模式:
    result = await orch.run(sm_mode="interactive_simulate")

    print("\nFinal result:", result)
    print("Final metadata:", orch.metadata)
    print("\nEvent log:")
    for ev in ctx.get("rehearsal").event_log:
        print(ev)


if __name__ == "__main__":
    asyncio.run(main())