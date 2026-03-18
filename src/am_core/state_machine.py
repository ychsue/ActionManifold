# src/am_core/state_machine.py

from __future__ import annotations
from sqlite3 import adapt
from typing import Any, Dict, List, Optional

from am_core.ctx.ctx_wrapper import WrappedCtx
from am_core.ctx.metadata_wrapper import MetadataDeltaCollector, WrappedMetadata

from typing import Generic, TypeVar

from typing import Mapping, MutableMapping

from am_core.interactive.types import InteractiveAdapter

TOutput = TypeVar("TOutput", bound=Mapping[str, Any])
TCtxWrite = TypeVar("TCtxWrite", bound=Mapping[str, Any])
TMetadata = TypeVar("TMetadata", bound=Mapping[str, Any])

class StateMachine(Generic[TOutput, TCtxWrite, TMetadata]):
    """
    三種模式（normal / preview / interactive_simulate）都共用同一套 domain logic：

    normal：compute + side effect
    preview：compute（無 side effect）
    interactive_simulate：compute（無 side effect）+ await_input

    ---    
    Schema and typing (optional)
    StateMachine supports optional generics to help IDEs and type checkers:
    
    See `examples/example_sm_with_type.py` with its test in `tests/test_typed_predict.py` for a demonstration of how to use generics to specify the expected output, ctx_delta, and metadata shapes.

    TypedDict optional keys are supported via typing_extensions.NotRequired. If you omit generics (class MySM(StateMachine):) the system remains fully functional; generics only improve editor/type-checker assistance.

    ---
    四個可複寫的方法：
    1. predict_output(self) -> TOutput：純計算，回傳 output
    2. predict_ctx_delta(self) -> list[TCtxWrite]：回傳 ctx_delta（list[dict]）
    3. predict_metadata_delta(self) -> TMetadata|dict：回傳 metadata_delta（dict）
    4. _run(self, wrapped_metadata) -> TOutput：真正執行 side effect 的方法，只有 normal 模式會執行。preview / interactive 模式不會執行。
       裡面在處理 output、ctx_delta、metadata_delta 的 side effect。這三個，可以透過呼叫 predict_output / predict_ctx_delta / predict_metadata_delta 來拿到預期的 output / delta，或直接用 self.wrapped_metadata.get() 來拿真實 metadata。
    """

    def __init__(self, wrapped_ctx: WrappedCtx, parent: Optional[Any] = None, name: Optional[str] = None):
        self.wrapped_ctx = wrapped_ctx
        self.parent = parent
        self.name = name

        self._metadata_delta = MetadataDeltaCollector()
        self.wrapped_metadata: Optional[WrappedMetadata] = None

    # ------------------------------------------------------------
    # 主入口：三種模式
    # ------------------------------------------------------------
    async def run(self, metadata, sm_mode="normal"):
        self.wrapped_metadata = WrappedMetadata(metadata, self._metadata_delta)

        # 1. 執行 domain logic（pure compute）
        output = await self.predict_output()
        ctx_delta = await self.predict_ctx_delta()
        metadata_delta = await self.predict_metadata_delta()
        
        actual_sm_mode = sm_mode
        adapter: Optional[InteractiveAdapter] = None
        if sm_mode == "interactive_simulate":
            # 如果是 interactive_simulate 模式，先由 truely_execute 來確認是否讓這個SM是真的執行，而非互動式模擬 (因為使用者可能想要讓他真的跑，好達到手動一步一步執行的效果）
            adapter = self.wrapped_ctx._real.get_interactive_adapter()
            if adapter is None:
                raise ValueError("Interactive mode requires an interactive adapter, but none was found in context.")
            truely_execute = await adapter.truely_execute()
            if truely_execute:
                actual_sm_mode = "normal"
            else:
                actual_sm_mode = "interactive_simulate"

        # 2. 三種模式決定 side effect 與 await_input
        if actual_sm_mode == "normal":
            output_run = await self._run(self.wrapped_metadata)
            ctx_delta_run = list(self.wrapped_ctx._delta.ops)  # 轉成一般 list，方便序列化
            metadata_delta_run = dict(self._metadata_delta.ops)
            # 確認這三個的keys 是否有分別在 output, ctx_delta, metadata_delta 三個變數中，如果沒有，要emit warning
            for key in output_run.keys():
                if key not in output:
                    self.emit({
                        "type": "warning",
                        "message": f"State {self.name}: output key '{key}' is not in predict_output() result",
                    })
            
            if len(ctx_delta) != 0:
                ## ctx_delta 與 ctx_delta_run 都先轉成 [item["mode"]_item["key"]] 的形式，然後才比較，好找出不同的 mode_key 來
                ctx_delta_mode_key_run = [f"{item['mode']}_{item['key']}" for item in ctx_delta_run]
                ctx_delta_mode_key = [f"{item['mode']}_{item['key']}" for item in ctx_delta]
                for mode_key in ctx_delta_mode_key_run:
                    if mode_key not in ctx_delta_mode_key:
                        self.emit({
                            "type": "warning",
                            "message": f"State {self.name}: ctx_delta key '{mode_key}' is not in predict_ctx_delta() result",
                        })
            if len(metadata_delta) != 0:
                for key in metadata_delta_run.keys():
                    if key not in metadata_delta:
                        self.emit({
                            "type": "warning",
                            "message": f"State {self.name}: metadata_delta key '{key}' is not in predict_metadata_delta() result",
                        })
            # 複寫 output, ctx_delta, metadata_delta 為真正執行的結果
            output = output_run
            ctx_delta = ctx_delta_run
            metadata_delta = metadata_delta_run
        elif actual_sm_mode == "interactive_simulate":
            # # interactive 模式：停下來等使用者
            # return {
            #     "status": "await_input",
            #     "is_SM": True,
            #     "sm_mode": actual_sm_mode,
            #     "output": output,
            #     "ctx_delta": ctx_delta,
            #     "metadata_delta": metadata_delta,
            #     "await": {
            #         "kind": "interactive_simulate",
            #         "state": self.name,
            #         "suggested": {
            #             "output": output,
            #             "ctx_delta": ctx_delta,
            #             "metadata_delta": metadata_delta,
            #         },
            #     },
            # }
            # interactive 模式：透過 adapter 來處理互動，並等待結果
            if adapter is None:
                raise ValueError("elif actual_sm_mode == 'interactive_simulate': Interactive mode requires an interactive adapter, but none was found in context.")
            modified = await adapter.handle({
                "kind": "await_input",
                "state": self.name if self.name else "unnamed_state",
                "suggested": {
                    "output": dict(output),
                    "ctx_delta": [dict(item) for item in ctx_delta],
                    "metadata_delta": dict(metadata_delta),
                },
                "ui_hint": self._ui_hint() if hasattr(self, "_ui_hint") else {},
            })
            output = modified["output"]
            ctx_delta = modified["ctx_delta"]
            metadata_delta = modified["metadata_delta"]

        # preview：不做 side effect，但仍然 apply delta（由 ORCH.after_decision）
        # normal：做 side effect

        # 3. 回傳結果（ORCH.after_decision 會 apply delta）
        return {
            "status": output.get("status", "ok"),
            "is_SM": True,
            "sm_mode": actual_sm_mode,
            "chain": self.get_chain(),
            "output": output,
            "ctx_delta": ctx_delta,
            "metadata_delta": metadata_delta,
        }

    #------------------------------------------------------------
    # 取得整個 orch->....->state 的 chain
    def get_chain(self) -> List[str]:
        chain = []
        current = self
        while current is not None:
            if current.name:
                chain.append(current.name)
            current = getattr(current, "parent", None)
        return list(reversed(chain))

    # ------------------------------------------------------------
    # event 冒泡
    # ------------------------------------------------------------
    def emit(self, event: Dict[str, Any]) -> None:
        """
        將事件往 parent 冒泡。
        parent 可以是 Orchestrator / World / 其他具備 emit 的物件。
        """
        if self.parent and hasattr(self.parent, "emit"):
            self.parent.emit(event)
    # ------------------------------------------------------------
    # Domain Logic（使用者覆寫這三個）
    # ------------------------------------------------------------
    async def predict_output(self) -> TOutput:
        """
        使用者覆寫：純計算，不做 side effect。
        """
        output: TOutput = {"status": "ok"}  # type: ignore
        return output

    async def predict_ctx_delta(self) -> list[TCtxWrite]:
        """
        使用者覆寫：回傳 ctx_delta（list[dict]）
        """
        return []

    async def predict_metadata_delta(self) -> TMetadata|dict:
        """
        使用者覆寫：回傳 metadata_delta（dict）
        """
        return dict[str, Any]()

    # ------------------------------------------------------------
    # Side Effect（只有 normal 模式會執行）
    # ------------------------------------------------------------
    async def _run(self, wrapped_metadata: WrappedMetadata) -> TOutput:
        """
        使用者可覆寫：真實 side effect（寫檔、API call、DB、外部世界）\\
        preview / interactive 模式不會執行。\\
        裡面在處理 output、ctx_delta、metadata_delta 的 side effect。\\
        這三個，可以透過呼叫 predict_output / predict_ctx_delta / predict_metadata_delta 來拿到預期的 output / delta，或直接用 self.wrapped_metadata.get() 來拿真實 metadata。
        """
        raise NotImplementedError

    def _ui_hint(self) -> Dict[str, Any]:
        """
        使用者可覆寫：提供給 interactive adapter 的 UI hint，讓 adapter 可以根據不同 state 顯示不同的 UI。
        """
        return {}