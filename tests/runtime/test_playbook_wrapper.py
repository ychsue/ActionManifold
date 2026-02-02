# tests/runtime/test_playbook_wrapper.py

from am_core.playbook import Playbook


class DummyStartState:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def run(self, metadata):
        return {"ok": True}


class DummyNextState:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def run(self, metadata):
        return {"ok": metadata.get("ok", False)}


example_playbook = {
    "initial": "StartState",
    "final": ["Success", "Error"],
    "states": [
        {
            "name": "StartState",
            "to": "NextState",
        },
        {
            "name": "NextState",
            "switch": {
                "ok == True": "Success",
                "ok == False": "Error",
            },
        },
    ],
    "registry": {
        "StartState": DummyStartState,
        "NextState": DummyNextState,
    },
}


def test_playbook_basic_semantics():
    pb = Playbook(example_playbook)

    assert pb.initial_state() == "StartState"
    assert pb.is_final("Success") is True
    assert pb.is_final("Error") is True
    assert pb.is_final("StartState") is False

    start_def = pb.get_state_def("StartState")
    assert start_def["to"] == "NextState"

    next_def = pb.get_state_def("NextState")
    assert "switch" in next_def
    assert next_def["switch"]["ok == True"] == "Success"


def test_playbook_instantiates_state_classes():
    pb = Playbook(example_playbook)

    start = pb.instantiate_state("StartState", foo=1)
    assert isinstance(start, DummyStartState)
    assert start.kwargs["foo"] == 1

    next_state = pb.instantiate_state("NextState", bar=2)
    assert isinstance(next_state, DummyNextState)
    assert next_state.kwargs["bar"] == 2


def test_playbook_transition_helpers():
    pb = Playbook(example_playbook)

    assert pb.get_next_state_by_default_transition("StartState") == "NextState"
    assert pb.get_next_state_by_default_transition("NextState") is None

    switch = pb.get_switch_mapping("NextState")
    if switch is None:
        raise AssertionError("Switch mapping should not be None")
    assert switch["ok == True"] == "Success"
    assert switch["ok == False"] == "Error"