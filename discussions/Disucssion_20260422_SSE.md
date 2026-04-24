# 試著串接runtime前後端

## [2026-04-22] ychsue 我覺得我們可以往SSE 與 UI 前進了。

### [2026-04-22] Copilot's Answer 01

很好，走到這裡你整個 runtime 基礎其實已經夠穩，可以開始「把呼吸拉到 UI 上」了。

我先幫你定一個最小但完整的互動迴路——**World ↔ SSE ↔ UI ↔ simulate_step API ↔ World**，你可以邊跑邊長。

---

#### 1. 事件流的骨架（先講整體節奏）

一個完整的 interactive_simulate 迴圈會長這樣：

1. 使用者在 UI 點「開始模擬」  
2. 後端呼叫 `world.simulate()`（背景 task）  
3. Orchestrator 每跑完一個 SM → `emit(wait_for_decision, ...)`  
4. World 把 `emit` 的事件透過 **SSE** 推到前端  
5. UI 收到 `wait_for_decision` → 顯示目前 ctx / metadata / chain / transition  
6. 使用者在 UI 點「繼續 / 重跑 / 分支 / 結束」  
7. UI 呼叫 `POST /simulate_step`，帶上：
   - `session_id`
   - `orch_id`
   - `decision`（例如 `{"action": "continue"}`）  
8. 後端找到對應的 World → `world.runtime_store.resolve_pending(orch_id, decision)`  
9. Orchestrator 的 `_wait_for_decision()` 被喚醒 → 繼續下一輪  
10. 重複 3–9，直到 final_state

你現在的 World + Orchestrator + RuntimeStore，其實已經具備 3、8、9 的能力了，我們只要把 4、5、6、7 補上。

---

#### 2. SSE endpoint（World → UI）

你已經有：

```python
def subscribe(self, callback): ...
def emit(self, event): ...
```

可以直接在 FastAPI（或你用的框架）裡包一個 SSE endpoint：

```python
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
import asyncio
import json

router = APIRouter()

@router.get("/events/{session_id}")
async def sse_events(session_id: str):
    world = session_manager.get(session_id)

    queue: asyncio.Queue = asyncio.Queue()

    def _on_event(ev):
        # 這裡可以先過濾，只推你要的 kind
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
```

UI 端就可以：

```js
const es = new EventSource(`/events/${sessionId}`);
es.onmessage = (e) => {
  const ev = JSON.parse(e.data);
  if (ev.kind === "wait_for_decision") {
    // render ctx / metadata / transition / orch_id
  }
};
```

---

#### 3. simulate_step API（UI → World）

這個 endpoint 就是你給 orchestrator「餵 decision」的入口。

```python
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

class SimulateStepInput(BaseModel):
    session_id: str
    orch_id: str
    decision: dict

@router.post("/simulate_step")
async def simulate_step(body: SimulateStepInput):
    world = session_manager.get(body.session_id)
    # 直接用 RuntimeStore 喚醒對應 orchestrator
    world.runtime_store.resolve_pending(body.orch_id, body.decision)
    return {"status": "ok"}
```

UI 端在收到 `wait_for_decision` 事件後，就可以：

```js
await fetch("/simulate_step", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    session_id,
    orch_id: ev.orch_id,
    decision: { action: "continue" }, // 或 retry / abort / branch...
  }),
});
```

---

#### 4. 啟動 simulate（World 端）

你已經有：

```python
world.start(sm_mode="interactive_simulate")
## 或
asyncio.create_task(world.simulate())
```

可以在 UI 這樣叫：

```python
@router.post("/simulate_start")
async def simulate_start(body: StartInput):
    world = session_manager.get(body.session_id)
    asyncio.create_task(world.simulate())
    return {"status": "started"}
```

UI：

```js
await fetch("/simulate_start", { method: "POST", ... });
```

---

#### 5. 你現在已經具備的資訊（不用再多設計）

`wait_for_decision` 事件裡你已經塞了這些：

```python
self.emit({
    "kind": "wait_for_decision",
    "orch_id": self.orch_id,
    "state": current_state,
    "parent_state": parent_state,
    "metadata": dict(self.metadata),
    "ctx": child_ctx.dump(),
    "transition": next_state,
    "timestamp": time.time(),
})
```

UI 可以直接拿來：

- 顯示目前在哪個 state  
- 顯示 chain（如果你想加也可以）  
- 顯示 ctx / metadata  
- 顯示下一個 transition（讓使用者知道「繼續」會去哪）  

這已經足夠做一個很有感的第一版 UI。

---

#### 6. 建議你先做的最小 UI 流程

1. 左側：顯示 playbook 結構（你已有 `describe_project()`）  
2. 右側上方：顯示目前 state / orch_id / chain  
3. 右側中間：顯示 ctx / metadata（JSON 展開即可）  
4. 右側下方：三個按鈕：
   - 「繼續」→ `decision = {"action": "continue"}`
   - 「結束」→ `decision = {"action": "finish"}`（或你定義的語意）
   - 「重跑」→ `decision = {"action": "retry"}`（未來用）

先把這條 loop跑順，你之後要加：

- parallel orchestrator  
- 多 session 切換  
- decision 面板（選擇下一個 state）  
- event log timeline  
- ctx tree diff  

都會非常自然。

---

如果你願意，下一步我可以幫你選一個具體技術棧（例如 FastAPI + HTMX / React / plain HTML）直接幫你寫出第一版前後端的「互動 simulate 控制台」骨架，讓你可以在瀏覽器裡看到整個 orchestrator 一步一步走。

=================================================================================
---

## [2026-04-22] ychsue 您少考慮 adapter for stateMachine 的問題了，會卡兩次，一次在adapter，一結束就是這個SSE了-_-
還有，這個FastAPI Server 建議放在哪個目錄呢？完整的MVP怎麼寫呢？

### [2026-04-22] ychsue 修正 01 等等，adapter 的目的是讓SM沒有真的跑，而是直接拿使用者透過adapter 給的 ctx_delta, metadata_delta 與 output，來讓他跑，所以，他才是用來決定往哪走的。因此我才說這個 interactive decision 功能有點重複了

### [2026-04-22] Copilot's Answer 02

你完全抓到核心：  
**StateMachine 的 adapter（interactive_adapter）本來就是「決定 SM output / ctx_delta / metadata_delta / transition」的來源。**  
而我剛才給你的 SSE + orchestrator `_wait_for_decision()` 方案，本質上又在做「決定 transition」這件事。

所以你現在看到的「卡兩次」不是 bug，而是：

#### ⭐ 你同時啟用了兩套互動決策機制  
1. **StateMachine adapter → 決定 SM output**  
2. **Orchestrator interactive_simulate → 決定 transition**

這兩套機制都在等 UI → 所以卡兩次。

而你真正想要的是：

> **interactive_simulate 模式下，adapter 就是 UI 的唯一決策來源，SSE 只是把 adapter 的需求送到 UI，而不是再卡一次 orchestrator。**

也就是說：

#### ⭐ SSE/UI 應該是 adapter 的「前端」，不是 orchestrator 的「第二層互動」。

這是整個架構的關鍵。

---

#### 🎯 你真正需要的架構（正確版）

##### ❌ 錯誤架構（你現在的）
```
StateMachine → adapter.ask() → 等 UI
Orchestrator → wait_for_decision() → 再等 UI
```

→ 卡兩次  
→ 邏輯重複  
→ UI 要回兩次 decision  
→ 不符合你的原始設計

---

##### ✔ 正確架構（你真正想要的）
```
StateMachine → adapter.ask() → UI → /simulate_step → adapter 回傳 output
Orchestrator → 不需要 wait_for_decision
```

也就是：

#### ⭐ interactive_simulate 模式下，adapter 是唯一的互動點  
#### ⭐ SSE 只是把 adapter 的問題送到 UI  
#### ⭐ UI 回答後 → /simulate_step → adapter.set_result()  
#### ⭐ orchestrator 不需要 `_wait_for_decision()`  

這樣：

- 不會卡兩次  
- 不會重複決策  
- SM output / ctx_delta / metadata_delta 都由 adapter 控制  
- Orchestrator 只負責執行 SM，不負責互動  
- SSE 只是事件通道，不是互動邏輯  

---

#### 🎯 那 orchestrator 的 `_wait_for_decision()` 要不要保留？

###### ✔ 在 interactive_simulate 模式下：  
**不應該使用 orchestrator 的 `_wait_for_decision()`。**

###### ✔ 在 normal 模式下：  
仍然可以保留（例如 debug、step-by-step、parallel orchestration 等用途）。

但 interactive_simulate 的互動應該完全交給 adapter。

---

#### 🎯 那 SSE 要送什麼事件？

不是 `wait_for_decision`（那是 orchestrator 的），  
而是 adapter 的事件，例如：

```
{
  "kind": "adapter_request",
  "orch_id": "...",
  "sm_id": "...",
  "prompt": "...",
  "ctx": {...},
  "metadata": {...},
  "options": [...],
}
```

UI 收到後：

- 顯示 prompt  
- 顯示 ctx  
- 顯示 metadata  
- 顯示 options（如果有）  
- 使用者選擇後 → `/simulate_step` → adapter.set_result()

---

#### 🎯 simulate_step API 要喚醒誰？

不是 orchestrator，而是 adapter。

例如：

```python
@app.post("/simulate_step")
async def simulate_step(body: SimulateStepInput):
    world = session_manager.get(body.session_id)
    adapter = world.runtime_store.get_adapter(body.sm_id)
    adapter.set_result(body.decision)
    return {"status": "ok"}
```

---

#### 🎯 FastAPI server 放哪裡？

建議：

```
src/
  am_core/          # 核心：orchestrator, SM, ctx, runtime_store
  am_server/        # API 層：FastAPI, SSE, simulate_step
    __init__.py
    api.py
    routes_simulate.py
    routes_events.py
    session_manager.py  # 或共用 am_core 的
```

理由：

- **am_core 不依賴 FastAPI**（乾淨、可測試、可嵌入）  
- **am_server 依賴 am_core**（API 層）  
- SSE/UI 只是 runtime 的一個前端，不應污染 core  

---

#### 🎯 MVP 完整流程（正確版）

###### 1. UI → `/simulate_start`  
後端：

```python
asyncio.create_task(world.simulate())
```

###### 2. SM 執行 → adapter.ask()  
adapter.ask() 會：

- 建立 future  
- 在 runtime_store 註冊 pending  
- emit `adapter_request` 事件（SSE）

###### 3. UI 收到 SSE → 顯示 prompt / ctx / metadata  
使用者按「continue / retry / branch / 自訂輸入」

###### 4. UI → `/simulate_step`  
後端：

```python
adapter.set_result(decision)
```

###### 5. SM.run() 繼續 → 回傳 output / ctx_delta / metadata_delta  
orchestrator 繼續下一個 state

###### 6. 重複直到 final_state

---

#### 🎉 最終總結（你現在完全理解了）

你說的完全正確：

> adapter 是用來決定 SM output / ctx_delta / metadata_delta 的  
> interactive decision 功能跟 adapter 重複了

所以正確做法是：

#### ⭐ interactive_simulate = adapter + SSE  
#### ❌ 不需要 orchestrator 的 wait_for_decision  
#### ❌ 不需要兩層互動  
#### ✔ UI → adapter → SM → orchestrator → 下一輪  

這樣：

- 不會卡兩次  
- 不會重複決策  
- 架構乾淨  
- UI 只需要處理 adapter 的互動  
- orchestrator 專心 orchestrate  
- runtime_store 只管理 pending adapter futures  

---

#### 🚀 下一步  
我可以幫你：

###### A. 設計「adapter_request」事件格式（SSE）  
###### B. 設計「simulate_step」API（喚醒 adapter）  
###### C. 幫你重寫 FakeAdapter（支援 SSE）  
###### D. 幫你寫完整的 FastAPI MVP（可直接跑）  
###### E. 幫你寫一個最小 UI（HTML + JS）可以完整走 simulate  

你想先做哪一個？

===================================================================
---

## [2026-04-22] ychsue 看來我們得想想 parallel orchestrator 下，adapter 的設計了，用lock如何？強制一次只有一個SM透過adapter 使用SSE或CLI或Anything else？

### [2026-04-22] Copilot's Answer 03

你這個問題問得超到點——**真正會「打架」的是 adapter，而不是 orchestrator 本身。**  
parallel orchestrator 一開，下列事情就會同時發生：

- 多個 SM 並行跑  
- 多個 SM 幾乎同時呼叫 `adapter.handle(await_input)`  
- 但底層 adapter 可能是：
  - CLI（一次只能問一個問題）  
  - SSE / Web UI（可以同時顯示多個問題）  

所以設計關鍵變成：

> **「並行 SM」可以同時呼叫 adapter，但「adapter 的具體實作」要自己決定能不能同時服務多個請求。**

---

#### 1. 原則：不要在 orchestrator 上鎖，在 adapter 上決定策略

- **Orchestrator / SM**：可以放心 parallel，照常 `await adapter.handle(...)`  
- **Adapter 實作**：自己決定要不要 serialize

也就是說：

- CLIAdapter：**需要 lock**（一次只允許一個互動）  
- SSEAdapter：**不需要 lock**（可以同時掛多個 pending，靠 ID 區分）

---

#### 2. CLIAdapter：用 lock 把互動序列化（你問的「用 lock 如何？」就放這裡）

```python
import asyncio
from ..types import InteractiveAdapter

class CLIAdapter(InteractiveAdapter):
    _lock = asyncio.Lock()  # class-level，所有 SM 共用

    async def handle(self, await_input: AwaitInput) -> ModifiedDecision:
        async with self._lock:
            # 這裡就是你原本的互動流程
            # 印 state / chain / ui_hint / suggested
            # 開 editor 或讀 stdin
            # 回傳 ModifiedDecision
            ...
```

效果：

- 多個 SM 並行呼叫 `handle()`  
- 但 CLIAdapter 會把它們排隊，一次只處理一個  
- 不會出現兩個 prompt 同時出現在 terminal 的混亂狀況  

這種「強制一次只有一個 SM 透過 CLI adapter」的語意，對 CLI 來說是合理的。

---

#### 3. SSE / Web UI adapter：不用 lock，用「await_id」+ RuntimeStore

這種 adapter 的目標是：

- 可以同時有多個 SM 在等 UI  
- UI 可以同時看到多個「問題卡片」  
- 使用者可以選擇先回哪一個  

做法是：

##### 3.1 在 `AwaitInput` 裡加一個 `await_id`

```python
await_input = {
    "await_id": uuid4().hex,
    "state": ...,
    "chain": ...,
    "suggested": {...},
    "ui_hint": {...},
}
```

##### 3.2 SSEAdapter.handle 的流程

```python
class SSEAdapter(InteractiveAdapter):
    def __init__(self, runtime_store: RuntimeStore):
        self.runtime = runtime_store

    async def handle(self, await_input: AwaitInput) -> ModifiedDecision:
        await_id = await_input["await_id"]

        loop = asyncio.get_event_loop()
        fut = loop.create_future()

        # 1. 把 future 註冊到 RuntimeStore（專門給 adapter 用的 pending）
        self.runtime.register_adapter_pending(await_id, fut)

        # 2. emit 事件給 SSE（World.emit → SSE）
        self.runtime.emit({
            "kind": "adapter_request",
            "await_id": await_id,
            "state": await_input["state"],
            "chain": await_input.get("chain"),
            "suggested": await_input["suggested"],
            "ui_hint": await_input.get("ui_hint", {}),
            "timestamp": time.time(),
        })

        # 3. 等 UI 回覆（/simulate_step → resolve_adapter_pending）
        decision = await fut

        # 4. 把 decision 轉成 ModifiedDecision
        return ModifiedDecision(
            output=decision["output"],
            ctx_delta=decision["ctx_delta"],
            metadata_delta=decision["metadata_delta"],
        )
```

##### 3.3 `/simulate_step` 對應的後端

```python
class SimulateStepInput(BaseModel):
    session_id: str
    await_id: str
    decision: dict  # {output, ctx_delta, metadata_delta}

@app.post("/simulate_step")
async def simulate_step(body: SimulateStepInput):
    world = session_manager.get(body.session_id)
    world.runtime_store.resolve_adapter_pending(body.await_id, body.decision)
    return {"status": "ok"}
```

這樣：

- 多個 SM 可以同時 `await adapter.handle()`  
- 每個 handle 都有自己的 `await_id`  
- UI 會看到多張卡片，每張卡片帶一個 `await_id`  
- 使用者回覆哪一張，就喚醒對應的 future  
- 完全不需要 lock  

---

#### 4. RuntimeStore 要多一組「adapter pending」

你現在的 RuntimeStore 大概長這樣：

```python
class WorldRuntimeStore(RuntimeStore):
    self.active_orchestrators = {}
    self.pending_decisions = {}
```

可以加一組：

```python
    self.adapter_pending = {}

    def register_adapter_pending(self, await_id: str, future):
        self.adapter_pending[await_id] = future

    def resolve_adapter_pending(self, await_id: str, decision: Any):
        fut = self.adapter_pending.get(await_id)
        if fut and not fut.done():
            fut.set_result(decision)
        self.adapter_pending.pop(await_id, None)
```

這樣 orchestrator 的 pending（如果你未來還要用）  
和 adapter 的 pending 是分開管理的。

---

#### 5. 回到你的問題：「用 lock 如何？」

**答案是：要看 adapter 類型：**

- **CLIAdapter / GUI 彈窗型**：  
  - 是「人眼一次只能看一個」的互動  
  - 用 `asyncio.Lock` 把 `handle()` 序列化是合理的  
  - 這個 lock 放在 adapter 裡，而不是 orchestrator 裡  

- **SSE / Web UI adapter**：  
  - UI 可以同時顯示多個問題  
  - 不需要 lock  
  - 用 `await_id + RuntimeStore` 來管理多個 pending  

也就是說：

> **parallel orchestrator 不需要被鎖住，adapter 才是決定「一次要服務幾個互動」的地方。**

---

如果你願意，下一步我可以幫你：

- 把 **SSEAdapter 的完整 MVP** 寫出來（含事件格式、RuntimeStore 介面、FastAPI `/simulate_step`）  
- 或者先幫你把 **CLIAdapter 加上 lock 的版本** 寫乾淨，讓 parallel SM 在 CLI 模式下也不會亂掉。

===============================================================
---

## [2026-04-23] ychsue 目前您給的範例，少了 Runtime.emit 的定義。其二，可以寫 am_runtime_server 的程式碼嗎？謝謝。

### [2026-04-23] Copilot's Answer 01

你抓得很細，這兩個點都關鍵：

1. 我前面用到 `self.runtime.emit(...)`，但 `RuntimeStore` 裡根本沒定義 emit  
2. 你想要一個實際可跑的 `am_runtime_server` 範例

我們就一次把這兩件事補完整，而且用「**World.emit 是事件源，RuntimeStore 只管 pending**」這個比較乾淨的分工。

---

#### 一、先補 RuntimeStore：加 adapter pending，但不負責 emit

`RuntimeStore` 只管「誰在等」，不管「事件怎麼送出去」：

```python
## src/am_core/runtime_store.py

from typing import Dict, Any
import abc

class RuntimeStore(abc.ABC):
    @abc.abstractmethod
    def register_adapter_pending(self, await_id: str, future) -> None: ...
    @abc.abstractmethod
    def resolve_adapter_pending(self, await_id: str, decision: Any) -> None: ...
    @abc.abstractmethod
    def get_adapter_pending(self) -> Dict[str, Any]: ...
    # 其他 orchestrator 用的 pending / active 你已經有了，就不重複

class WorldRuntimeStore(RuntimeStore):
    def __init__(self):
        self.active_orchestrators: Dict[str, Any] = {}
        self.pending_decisions: Dict[str, Any] = {}
        self.adapter_pending: Dict[str, Any] = {}

    # --- adapter pending ---
    def register_adapter_pending(self, await_id: str, future) -> None:
        self.adapter_pending[await_id] = future

    def resolve_adapter_pending(self, await_id: str, decision: Any) -> None:
        fut = self.adapter_pending.get(await_id)
        if fut and not fut.done():
            fut.set_result(decision)
        self.adapter_pending.pop(await_id, None)

    def get_adapter_pending(self) -> Dict[str, Any]:
        return dict(self.adapter_pending)
```

> 事件的 emit 一律走 `World.emit(event)`，不要塞進 RuntimeStore，這樣 core 邏輯比較乾淨。

---

#### 二、SSEAdapter：透過「注入的 emit 函數」丟事件

Adapter 不知道 World，只知道有個 `emit(event)` 可以叫：

```python
## src/am_core/interactive/sse_adapter.py

import asyncio
import time
import uuid
from typing import Callable

from am_core.runtime_store import RuntimeStore
from am_core.types import AwaitInput, InteractiveAdapter, ModifiedDecision

class SSEAdapter(InteractiveAdapter):
    def __init__(self, runtime_store: RuntimeStore, emit: Callable[[dict], None]):
        self.runtime = runtime_store
        self.emit = emit  # 通常就是 world.emit

    async def handle(self, await_input: AwaitInput) -> ModifiedDecision:
        await_id = uuid.uuid4().hex
        loop = asyncio.get_event_loop()
        fut = loop.create_future()

        self.runtime.register_adapter_pending(await_id, fut)

        self.emit({
            "kind": "adapter_request",
            "await_id": await_id,
            "state": await_input["state"],
            "chain": await_input.get("chain"),
            "suggested": await_input["suggested"],
            "ui_hint": await_input.get("ui_hint", {}),
            "timestamp": time.time(),
        })

        decision = await fut  # 期待格式：{output, ctx_delta, metadata_delta}

        return ModifiedDecision(
            output=decision["output"],
            ctx_delta=decision["ctx_delta"],
            metadata_delta=decision["metadata_delta"],
        )
```

在 `World` 裡要用這個 adapter，只要：

```python
from am_core.interactive.sse_adapter import SSEAdapter

self.runtime_store = WorldRuntimeStore()
self.root = Orchestrator(..., runtime_store=self.runtime_store, ...)

## 給 root ctx 一個 adapter（你原本就有 set_interactive_adapter）
self.ctx.set_interactive_adapter(
    SSEAdapter(runtime_store=self.runtime_store, emit=self.emit)
)
```

---

#### 三、`am_runtime_server`：一個可跑的 FastAPI MVP

假設你放在 `src/am_runtime_server/app.py`：

```python
## src/am_runtime_server/app.py

import asyncio
import json
from typing import Dict

from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from am_core.playbook import Playbook
from am_core.world import World
from am_core.session_manager import SessionManager  # 你已有

app = FastAPI()
session_manager = SessionManager()

## ---------- Pydantic models ----------

class CreateSessionInput(BaseModel):
    playbook_data: Dict
    base_path: str | None = None

class SimulateStartInput(BaseModel):
    session_id: str

class SimulateStepInput(BaseModel):
    session_id: str
    await_id: str
    decision: Dict  # {output, ctx_delta, metadata_delta}

## ---------- endpoints ----------

@app.post("/sessions")
def create_session(body: CreateSessionInput):
    pb = Playbook(body.playbook_data, base_path=body.base_path)
    session_id = session_manager.create(pb)
    world = session_manager.get(session_id)

    # 這裡把 SSEAdapter 掛上去
    from am_core.interactive.sse_adapter import SSEAdapter
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
```

啟動：

```bash
uvicorn am_runtime_server.app:app --reload
```

---

#### 四、前端怎麼接（最小概念版）

1. 建 session：

```js
const res = await fetch("/sessions", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ playbook_data, base_path }),
});
const { session_id } = await res.json();
```

2. 開 SSE：

```js
const es = new EventSource(`/events/${session_id}`);
es.onmessage = (e) => {
  const ev = JSON.parse(e.data);
  if (ev.kind === "adapter_request") {
    // 顯示 ev.state / ev.suggested / ev.ui_hint
    // 把 await_id 存起來
  }
};
```

3. 開始 simulate：

```js
await fetch("/simulate_start", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ session_id }),
});
```

4. 使用者在 UI 上編輯 output / ctx_delta / metadata_delta 後：

```js
await fetch("/simulate_step", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    session_id,
    await_id,      // 從 adapter_request 事件拿到
    decision: {
      output,
      ctx_delta,
      metadata_delta,
    },
  }),
});
```

---

這樣一來：

- **互動唯一入口是 adapter（SSEAdapter / CLIAdapter / FakeAdapter）**
- **parallel orchestrator 下，多個 SM 可以同時呼叫 adapter**
- CLIAdapter 用 lock 序列化互動  
- SSEAdapter 用 `await_id + RuntimeStore` 支援多個 pending  
- World.emit 是事件源，SSE 只是把它轉成 HTTP stream  

如果你願意，下一步我們可以專門針對「SSEAdapter + RuntimeStore 的測試」寫一個小測試檔，確保多個 SM 並行時，每個 await_id 都能被正確喚醒。

#### 🚀 下一步
你想要我幫你：

[ ] **A**. 幫你把 orchestrator 的 _wait_for_decision() 移除，改成純 adapter-based interactive simulate

[ ] **B**. 幫你寫完整的 SSEAdapter（含 await_id、事件格式、RuntimeStore 整合）

[ ] **C**. 幫你寫完整的 am_runtime_server（可直接跑）

[ ] **D**. 幫你寫一個最小 UI（HTML + JS）可以完整走 simulate
你選一個，我馬上幫你做。