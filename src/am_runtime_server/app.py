# src/am_runtime_server/app.py

import asyncio
import json
from pathlib import Path
from typing import Dict

from fastapi import FastAPI
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel

from am_core.interactive.adapters.sse_adapter import SSEAdapter
from am_core.playbook import Playbook
from am_core.runtime_cli.cli import init_project
from am_core.world import World
from am_core.session_manager import SessionManager  # 你已有

app = FastAPI()
session_manager = SessionManager()
BASE_DIR = Path(__file__).resolve().parent

# ---------- Pydantic models ----------

class CreateSessionInput(BaseModel):
    project_root: str | None = None  # 如果沒有提供，就用 template_project 建立一個新的 project

class SimulateStartInput(BaseModel):
    session_id: str

class SimulateStepInput(BaseModel):
    session_id: str
    await_id: str
    decision: Dict  # {output, ctx_delta, metadata_delta}

# ---------- endpoints ----------

@app.get("/")
def read_root():
    return FileResponse(BASE_DIR / "index.html")

# -----------------------------
# Create Session
# -----------------------------
@app.post("/sessions")
def create_session(body: CreateSessionInput):
    """
    建立一個 session：
    1. 建立 work_dir: C:/Temp/<session_id>/
    2. 若 project_root=None → 用 template_project 建立一個 project
    3. 載入 playbook.yaml
    4. 建立 World
    5. 掛上 SSEAdapter
    """

    # 1. 建立 session
    session_id = session_manager.create(Playbook({"initial": "dummy"}))  # 先佔位
    world = session_manager.get(session_id)

    # 2. 建立 work_dir
    work_dir = Path("C:/Temp") / session_id
    work_dir.mkdir(parents=True, exist_ok=True)

    # 3. 建立 project_root
    if body.project_root:
        project_root = Path(body.project_root)
    else:
        # 用 template_project 建立一個 project
        project_root = work_dir / "project"
        init_project(str(project_root))

    # 4. 載入 playbook.yaml
    pb_path = project_root / "playbook.yaml"
    pb = Playbook.load_from_file(str(pb_path))

    # 5. 重建 World（覆蓋 placeholder）
    world = World(pb, name=session_id)
    world.work_dir = work_dir  # <--- 記錄 work_dir
    session_manager.sessions[session_id] = world

    # 6. 掛上 SSEAdapter
    world.ctx.set_interactive_adapter(
        SSEAdapter(runtime_store=world.runtime_store, emit=world.emit)
    )

    return {
        "session_id": session_id,
        "work_dir": str(work_dir),
        "project_root": str(project_root),
    }


# -----------------------------
# Start simulate
# -----------------------------
@app.post("/simulate_start")
async def simulate_start(body: SimulateStartInput):
    world = session_manager.get(body.session_id)
    asyncio.create_task(world.simulate())  # interactive 模式
    return {"status": "started"}


# -----------------------------
# simulate_step
# -----------------------------
@app.post("/simulate_step")
async def simulate_step(body: SimulateStepInput):
    world = session_manager.get(body.session_id)
    world.runtime_store.resolve_adapter_pending(body.await_id, body.decision)
    return {"status": "ok"}


# -----------------------------
# SSE events
# -----------------------------
@app.get("/events/{session_id}")
async def sse_events(session_id: str):
    world = session_manager.get(session_id)
    queue: asyncio.Queue = asyncio.Queue()

    def _on_event(ev):
        queue.put_nowait(ev)

    world.subscribe(_on_event)

    async def event_stream():
        try:
            while True:
                ev = await queue.get()
                yield f"data: {json.dumps(ev)}\n\n"
        finally:
            world.unsubscribe(_on_event)

    return StreamingResponse(event_stream(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)