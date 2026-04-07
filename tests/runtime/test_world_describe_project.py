import yaml
from pathlib import Path
from am_core.world import World
from am_core.playbook import Playbook

def write_yaml(path, data):
    Path(path).write_text(yaml.safe_dump(data))

def test_world_describe_project(tmp_path):
    # root playbook
    root_pb = {
        "initial": "step1",
        "final": ["step2"],
        "states": [
            {"name": "step1", "class_": "proj.states.step1.Step1", "to": "step2"},
            {"name": "step2", "class_": "proj.states.step2.Step2"},
            {"name": "subA", "subflow": {"initial": "a1", "states": [
                {"name": "a1", "class_": "proj.subflows.a.states.a1.A1", "to": "a2"},
                {"name": "a2", "class_": "proj.subflows.a.states.a2.A2"},
            ]}}
        ]
    }

    root_path = tmp_path / "playbook.yaml"
    write_yaml(root_path, root_pb)

    pb = Playbook(root_pb, base_path=str(tmp_path))
    world = World(pb)

    desc = world.describe_project()

    assert desc["path"] == ["root"]
    assert "step1" in desc["states"]
    assert "step2" in desc["states"]
    assert len(desc["subflows"]) == 1

    sub = desc["subflows"][0]
    assert sub["path"] == ["root", "subA"]
    assert "a1" in sub["states"]
    assert "a2" in sub["states"]