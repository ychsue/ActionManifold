import asyncio
from am_core.ctx.context import Ctx
from am_core.orchestrator import Orchestrator, Rehearsal
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine


class CountSM(StateMachine):
    async def predict_output(self):
        return {"status": "ok", "value": self.wrapped_ctx.get("count", 0)}

    async def predict_ctx_delta(self):
        count = self.wrapped_ctx.get("count", 0)
        return [{"mode": "root", "key": "count", "to": count + 1}]

    async def predict_metadata_delta(self):
        return {"last_state": self.name}

    async def _run(self, wrapped_metadata):
        # 真正執行 side effect
        count = self.wrapped_ctx.get("count", 0)
        self.wrapped_ctx.set_root("count", count + 1)
        wrapped_metadata.set("last_state", self.name)
        return {"status": "ok"}


def make_playbook():
    return Playbook({
        "states": [
            {"name": "A", "to": "B"},
            {"name": "B", "switch": {
                "A": "A",
                "C": "C",
                }},
            {"name": "C", "to": None},
        ],
        "initial": "A",
        "registry": {
            "A": CountSM,
            "B": CountSM,
            "C": CountSM,
        }
    })


async def run_interactive():
    ctx = Ctx()
    pb = make_playbook()

    # 使用 CLIAdapter
    ctx.set_interactive_adapter("am_core.interactive.adapters.cli_adapter.CLIAdapter")

    orch = Orchestrator(pb, ctx)

    print("=== Running in interactive_simulate mode ===")
    result = await orch.run(sm_mode="interactive_simulate")

    print("\n=== Final result ===")
    print(result)
    print("\n=== Final ctx ===")
    print(ctx.flatten())
    print("\n=== Event log ===")
    for ev in ctx.get("rehearsal").event_log:
        print(ev)


async def run_resume():
    print("\n=== RESUME MODE ===")

    # 讀取上一次的 event_log
    # 在真實世界，你會從 work_dir 讀取
    # 這裡直接從記憶體複製
    ctx_prev = Ctx()
    pb = make_playbook()
    orch_prev = Orchestrator(pb, ctx_prev)
    await orch_prev.run()
    event_log = ctx_prev.get("rehearsal").event_log.copy()

    # resume 從 B 的 after_decision
    resume_id = None
    for ev in event_log:
        if ev["state"] == "B" and ev["kind"] == "after_decision":
            resume_id = ev["id"]
            break

    ctx2 = Ctx()
    ctx2.set("rehearsal", Rehearsal(
        mode="resume",
        event_log=event_log,
        resume_from_event_id=resume_id,
    ))

    orch2 = Orchestrator(pb, ctx2)
    result2 = await orch2.run()

    print("\n=== Resume result ===")
    print(result2)
    print("\n=== Resume ctx ===")
    print(ctx2.flatten())


if __name__ == "__main__":
    asyncio.run(run_interactive())
    # asyncio.run(run_resume())
