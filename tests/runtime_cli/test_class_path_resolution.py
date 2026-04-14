import sys
from am_core.runtime_cli.cli import init_project
from am_core.playbook import Playbook
from am_core.world import World
from am_core.state_machine import StateMachine
from am_core.orchestrator import Orchestrator

def test_class_path_resolution(tmp_path):
    # --- 1. 使用 init_project 建立完整 template ---
    init_project(str(tmp_path))

    # --- 2. load root playbook ---
    pb = Playbook.load_from_file(tmp_path / "playbook.yaml")
    world = World(pb)

    # --- 3. 測試 root state: step1 (.states.step1.Step1) ---
    orch = world.root
    state_def, child_ctx, child = orch.ini_child("step1", parent_state="root")

    assert isinstance(child, StateMachine)
    assert child.__class__.__name__ == "Step1"

    # --- 4. 測試 nested orchestrator: subflow_a ---
    ctor = pb.get_state_constructor("subflow_a")
    sub_orch = orch._instantiate_child("subflow_a", child_ctx, ctor)
    assert isinstance(sub_orch, Orchestrator)

    # --- 5. 測試 nested state: a1 (.states.a1.A1) ---
    sub_state_def, sub_child_ctx, sub_child = sub_orch.ini_child("a1", parent_state="subflow_a")
    assert isinstance(sub_child, StateMachine)
    assert sub_child.__class__.__name__ == "A1"

    # --- 6. 測試 nested state: a2 (.states.a2.A2) ---
    sub_state_def2, sub_child_ctx2, sub_child2 = sub_orch.ini_child("a2", parent_state="subflow_a")
    assert isinstance(sub_child2, StateMachine)
    assert sub_child2.__class__.__name__ == "A2"


def test_absolute_class_path_requires_user_import_context(tmp_path, monkeypatch):
    shared_pkg = tmp_path / "shared_pkg"
    shared_pkg.mkdir()
    (shared_pkg / "__init__.py").write_text("", encoding="utf-8")
    (shared_pkg / "shared_state.py").write_text(
        "from am_core.state_machine import StateMachine\n\n"
        "class SharedState(StateMachine):\n"
        "    async def predict_output(self):\n"
        "        return {'status': 'ok'}\n",
        encoding="utf-8",
    )

    pb = Playbook(
        {
            "initial": "shared",
            "final": ["shared"],
            "states": [
                {
                    "name": "shared",
                    "class_": "shared_pkg.shared_state.SharedState",
                }
            ],
        },
        base_path=str(tmp_path),
    )

    original_sys_path = list(sys.path)
    with monkeypatch.context() as context:
        context.setattr(sys, "path", list(original_sys_path))
        try:
            pb.get_state_constructor("shared")
        except ModuleNotFoundError:
            pass
        else:
            raise AssertionError("Absolute class paths should fail without user-managed import context")

    monkeypatch.syspath_prepend(str(tmp_path))
    ctor = pb.get_state_constructor("shared")

    assert issubclass(ctor["class_"], StateMachine)
    assert ctor["class_"].__name__ == "SharedState"
