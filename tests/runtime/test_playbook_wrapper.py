# tests/runtime/test_playbook_wrapper.py

import json
import os
import pytest

from am_core.playbook import Playbook


# ----------------------------------------
# 測試用的 dummy class
# ----------------------------------------
class DummyState:
    pass


# ----------------------------------------
# 測試 inline registry
# ----------------------------------------
def test_inline_registry_class():
    pb = Playbook({
        "initial": "A",
        "final": [],
        "states": [
            {"name": "A"}
        ],
        "registry": {
            "A": DummyState
        }
    })

    ctor = pb.get_state_constructor("A")
    assert ctor["kind"] == "python"
    assert ctor["class"] is DummyState


# ----------------------------------------
# 測試 python:module.Class 動態載入
# ----------------------------------------
def test_python_type_loading(tmp_path):
    # 建立一個臨時 python module
    module_path = tmp_path / "mymod.py"
    module_path.write_text("class X:\n    pass\n")

    # 加入 sys.path
    import sys
    sys.path.insert(0, str(tmp_path))

    pb = Playbook({
        "initial": "A",
        "final": [],
        "states": [
            {"name": "A", "type": "python:mymod.X"}
        ]
    })

    ctor = pb.get_state_constructor("A")
    assert ctor["kind"] == "python"
    assert ctor["class"].__name__ == "X"


# ----------------------------------------
# 測試 nested playbook: playbook:sub.json
# ----------------------------------------
def test_nested_playbook_loading(tmp_path):
    # 建立 subflow.json
    subflow = {
        "initial": "B",
        "final": [],
        "states": [
            {"name": "B"}
        ]
    }
    sub_path = tmp_path / "subflow.json"
    sub_path.write_text(json.dumps(subflow))

    # 建立 main playbook
    main_pb = Playbook({
        "initial": "A",
        "final": [],
        "states": [
            {"name": "A", "type": "playbook:subflow.json"}
        ]
    }, base_path=str(tmp_path))

    ctor = main_pb.get_state_constructor("A")
    assert ctor["kind"] == "orchestrator"
    assert isinstance(ctor["playbook"], Playbook)
    assert ctor["playbook"].initial_state() == "B"


# ----------------------------------------
# 測試 world:world.json
# ----------------------------------------
def test_world_loading(tmp_path):
    # 建立 world.json
    world_cfg = {
        "workdir": "/tmp/world1",
        "playbook": {
            "initial": "C",
            "final": [],
            "states": [
                {"name": "C"}
            ]
        }
    }
    world_path = tmp_path / "world.json"
    world_path.write_text(json.dumps(world_cfg))

    pb = Playbook({
        "initial": "A",
        "final": [],
        "states": [
            {"name": "A", "type": "world:world.json"}
        ]
    }, base_path=str(tmp_path))

    ctor = pb.get_state_constructor("A")
    assert ctor["kind"] == "world"
    assert ctor["workdir"] == "/tmp/world1"
    assert isinstance(ctor["playbook"], Playbook)
    assert ctor["playbook"].initial_state() == "C"