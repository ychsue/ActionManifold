# tests/runtime/test_playbook_wrapper.py

import pytest

from am_core.ctx.context import Ctx
from am_core.playbook import Playbook
from am_core.state_machine import StateMachine
from am_core.orchestrator import Orchestrator


# ---------------------------------------------------------
# 測試用 SM
# ---------------------------------------------------------
class A(StateMachine):
    async def _run(self, wrapped_metadata):
        return {"status": "ok"}


class B(StateMachine):
    async def _run(self, wrapped_metadata):
        return {"status": "ok"}


class C(StateMachine):
    async def _run(self, wrapped_metadata):
        return {"status": "ok"}


# ---------------------------------------------------------
# 1. states → ctor（本地宣告）
# ---------------------------------------------------------
def test_playbook_wrapper_states_ctor():
    pb = Playbook({
        "initial": "A",
        "final": ["A"],
        "states": [
            {"name": "A", "class": "tests.runtime.test_playbook_wrapper.A"},
        ],
        "registry": {}
    })

    ctor = pb.get_state_constructor("A")

    assert ctor["class"].__name__ == "A"
    assert ctor["subflow"] is None
    assert ctor["workdir"] is None


# ---------------------------------------------------------
# 2. registry → ctor（外部注入）
# ---------------------------------------------------------
def test_playbook_wrapper_registry_ctor():
    pb = Playbook({
        "initial": "A",
        "final": ["A"],
        "states": [
            {"name": "A"},  # states 沒宣告 class → 用 registry
        ],
        "registry": {
            "A": {
                "class": B
            }
        }
    })

    ctor = pb.get_state_constructor("A")

    assert ctor["class"].__name__ == "B"
    assert ctor["subflow"] is None
    assert ctor["workdir"] is None


# ---------------------------------------------------------
# 3. states override registry
# ---------------------------------------------------------
def test_playbook_wrapper_states_override_registry():
    pb = Playbook({
        "initial": "A",
        "final": ["A"],
        "states": [
            {"name": "A", "class": "tests.runtime.test_playbook_wrapper.C"},
        ],
        "registry": {
            "A": {
                "class": B
            }
        }
    })

    ctor = pb.get_state_constructor("A")

    # states > registry
    assert ctor["class"].__name__ == "C"


# ---------------------------------------------------------
# 4. subflow（巢狀 Playbook）
# ---------------------------------------------------------
def test_playbook_wrapper_subflow():
    sub_pb_dict = {
        "initial": "B",
        "final": ["B"],
        "states": [
            {"name": "B", "class": "tests.runtime.test_playbook_wrapper.B"}
        ],
        "registry": {}
    }

    pb = Playbook({
        "initial": "A",
        "final": ["A"],
        "states": [
            {
                "name": "A",
                # "class": "am_core.orchestrator.Orchestrator",
                "subflow": sub_pb_dict
            }
        ],
        "registry": {}
    })

    ctor = pb.get_state_constructor("A")

    assert issubclass(ctor["class"], Orchestrator)
    assert ctor["subflow"].initial == "B"
    assert ctor["subflow"].states["B"]["name"] == "B"


# ---------------------------------------------------------
# 5. builtin（Success / Error / Fail）
# ---------------------------------------------------------
def test_playbook_wrapper_builtin():
    pb = Playbook({
        "initial": "Success",
        "final": ["Success"],
        "states": [
            {"name": "Success", "builtin": "Success"}
        ],
        "registry": {}
    })

    ctor = pb.get_state_constructor("Success")

    # builtin SuccessStateMachine
    assert ctor["class"].__name__ == "SuccessStateMachine"