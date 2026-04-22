from am_core.runtime_cli.cli import init_project
from am_core.session_manager import SessionManager
from am_core.playbook import Playbook

def test_session_manager_create_and_get(tmp_path):
    # 建立一個簡單 playbook
    pb_data = {
        "initial": "step1",
        "final": ["step1"],
        "states": [
            {"name": "step1", "class_": ".states.step1.Step1"}
        ]
    }
    pb = Playbook(pb_data, base_path=str(tmp_path))

    sm = SessionManager()

    # 建立 session
    session_id = sm.create(pb)
    assert session_id in sm.sessions

    # 取得 world
    world = sm.get(session_id)
    assert world.playbook.initial_state() == "step1"

def test_session_manager_missing_session():
    sm = SessionManager()
    try:
        sm.get("not_exist")
        assert False, "should raise"
    except KeyError:
        assert True

def test_session_manager_with_template(tmp_path):
    # 產生 template project
    init_project(str(tmp_path))

    pb = Playbook.load_from_file(tmp_path / "playbook.yaml")

    sm = SessionManager()
    session_id = sm.create(pb)

    world = sm.get(session_id)
    assert world.playbook.initial_state() == "step1"