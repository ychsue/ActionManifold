import os
from pathlib import Path
from am_core.runtime_cli.cli import init_project
from am_core.playbook import Playbook
from am_core.world import World
import yaml

def test_am_run_init_and_describe_project(tmp_path):
    # 1. run am-run init
    init_project(str(tmp_path))

    # 2. check files exist
    assert (tmp_path / "playbook.yaml").exists()
    assert (tmp_path / "states" / "step1.py").exists()
    assert (tmp_path / "subflows" / "subflow_a" / "playbook.yaml").exists()

    # 3. load playbook
    pb = Playbook.load_from_file(tmp_path / "playbook.yaml")

    # 4. create world
    world = World(pb)

    # 5. describe project
    desc = world.describe_project()

    # 6. assertions
    assert desc["chain"] == ["root"]
    assert "step1" in desc["states"]
    assert len(desc["subflows"]) == 1

    sub = desc["subflows"][0]
    assert sub["chain"] == ["root", "subflow_a"]
    assert "a1" in sub["states"]
    assert "a2" in sub["states"]