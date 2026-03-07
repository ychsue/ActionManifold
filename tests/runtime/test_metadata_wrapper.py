
from am_core.ctx.metadata_wrapper import MetadataDeltaCollector, WrappedMetadata


def test_metadata_set_does_not_modify_real_metadata():
    real = {"a": 1}
    delta = MetadataDeltaCollector()
    wrapped = WrappedMetadata(real, delta)

    wrapped.set("a", 2)

    assert real["a"] == 1
    assert delta.ops == {"a": 2}


def test_metadata_get_reads_delta_first():
    real = {"a": 1}
    delta = MetadataDeltaCollector()
    wrapped = WrappedMetadata(real, delta)

    wrapped.set("a", 99)

    assert wrapped.get("a") == 99


def test_metadata_get_falls_back_to_real():
    real = {"a": 1}
    delta = MetadataDeltaCollector()
    wrapped = WrappedMetadata(real, delta)

    assert wrapped.get("a") == 1


def test_orch_after_decision_applies_metadata_delta():
    from am_core.ctx.context import Ctx
    from am_core.orchestrator import Orchestrator
    from am_core.playbook import Playbook
    from am_core.state_machine import StateMachine

    # 建立一個最小 playbook
    pb = Playbook({
        "states": [
            {"name": "A"},
        ],
        "registry": {
            "A": {"class": StateMachine},
        },
        "initial": "A"
    })

    ctx = Ctx()
    orch = Orchestrator(pb, ctx)

    # 模擬 SM 回傳 metadata_delta
    sm_output = {
        "is_SM": True,
        "ctx_delta": [],
        "metadata_delta": {"x": 42},
        "output": {},
    }

    enriched = {"event": {"output": sm_output}}

    orch.after_decision(
        event_id="1",
        current_state="A",
        parent_state="Root",
        enriched=enriched,
        child_ctx=ctx,
        next_state=None,
        rehearsal=ctx.get("rehearsal"),
        restore_event=False,
    )

    assert orch.metadata["x"] == 42