# tests/runtime/test_decision_block.py

from am_core.playbook import Playbook
from am_core.decision_block import decision_block


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
            "timeout": 30,
            "retry_times": 3,
            "switch": {
                "ok": "Success",
                "fail": "Error",
                "timeout": "Error",
                "retry": "StartState",
            },
        },
    ],
    "registry": {},
}


def test_linear_transition():
    """
    若 state_def 只有 'to'，decision_block 應該直接回傳該 next_state。
    """
    pb = Playbook(example_playbook)

    enriched = {"status": "ok"}  # status 不影響 linear transition

    next_state = decision_block(
        playbook=pb,
        current_state="StartState",
        enriched_output=enriched,
    )

    assert next_state == "NextState"


def test_switch_ok():
    pb = Playbook(example_playbook)

    enriched = {"status": "ok"}

    next_state = decision_block(
        playbook=pb,
        current_state="NextState",
        enriched_output=enriched,
    )

    assert next_state == "Success"


def test_switch_retry():
    pb = Playbook(example_playbook)

    enriched = {"status": "retry"}

    next_state = decision_block(
        playbook=pb,
        current_state="NextState",
        enriched_output=enriched,
    )

    assert next_state == "StartState"


def test_switch_fail():
    pb = Playbook(example_playbook)

    enriched = {"status": "fail"}

    next_state = decision_block(
        playbook=pb,
        current_state="NextState",
        enriched_output=enriched,
    )

    assert next_state == "Error"


def test_switch_timeout():
    pb = Playbook(example_playbook)

    enriched = {"status": "timeout"}

    next_state = decision_block(
        playbook=pb,
        current_state="NextState",
        enriched_output=enriched,
    )

    assert next_state == "Error"


def test_missing_switch_key_returns_none():
    """
    若 enriched_output["status"] 不在 switch 裡，回傳 None。
    """
    pb = Playbook(example_playbook)

    enriched = {"status": "unknown_status"}

    next_state = decision_block(
        playbook=pb,
        current_state="NextState",
        enriched_output=enriched,
    )

    assert next_state is None


def test_final_state_has_no_next():
    """
    final state 不應該再 transition。
    """
    pb = Playbook(example_playbook)

    enriched = {"status": "ok"}

    next_state = decision_block(
        playbook=pb,
        current_state="Success",
        enriched_output=enriched,
    )

    assert next_state is None