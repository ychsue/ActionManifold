import uuid
from typing import Dict
from am_core.world import World
from am_core.playbook import Playbook

class SessionManager:
    """
    管理多個 World（每個 session 一個 World）
    """

    def __init__(self):
        self.sessions: Dict[str, World] = {}

    def create(self, playbook: Playbook) -> str:
        """
        建立一個新的 World session，回傳 session_id
        """
        session_id = uuid.uuid4().hex
        world = World(playbook)
        self.sessions[session_id] = world
        return session_id

    def get(self, session_id: str) -> World:
        """
        取得指定 session 的 World
        """
        if session_id not in self.sessions:
            raise KeyError(f"Session {session_id} not found")
        return self.sessions[session_id]

    def delete(self, session_id: str):
        """
        刪除 session（可選）
        """
        if session_id in self.sessions:
            del self.sessions[session_id]
