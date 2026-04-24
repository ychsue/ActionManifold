# src/am_runtime_server/app.py

import asyncio
import json
from typing import Dict

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from am_core.interactive.adapters.sse_adapter import SSEAdapter
from am_core.playbook import Playbook
from am_core.world import World
from am_core.session_manager import SessionManager  # 你已有

app = FastAPI()
session_manager = SessionManager()

# ---------- Pydantic models ----------

class CreateSessionInput(BaseModel):
    playbook_data: Dict
    base_path: str | None = None

class SimulateStartInput(BaseModel):
    session_id: str

class SimulateStepInput(BaseModel):
    session_id: str
    await_id: str
    decision: Dict  # {output, ctx_delta, metadata_delta}

# ---------- endpoints ----------

@app.post("/sessions")
def create_session(body: CreateSessionInput):
    pb = Playbook(body.playbook_data, base_path=body.base_path)
    session_id = session_manager.create(pb)
    world = session_manager.get(session_id)

    # 這裡把 SSEAdapter 掛上去
    world.ctx.set_interactive_adapter(
        SSEAdapter(runtime_store=world.runtime_store, emit=world.emit)
    )

    return {"session_id": session_id}

@app.post("/simulate_start")
async def simulate_start(body: SimulateStartInput):
    world = session_manager.get(body.session_id)
    asyncio.create_task(world.simulate())  # interactive_simulate 模式
    return {"status": "started"}

@app.post("/simulate_step")
async def simulate_step(body: SimulateStepInput):
    world = session_manager.get(body.session_id)
    world.runtime_store.resolve_adapter_pending(body.await_id, body.decision)
    return {"status": "ok"}

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