# am_core/interactive/types.py
from typing import Any, Dict, List
from typing_extensions import TypedDict, NotRequired


class AwaitSuggested(TypedDict):
    output: Dict[str, Any]
    ctx_delta: List[Dict[str, Any]]
    metadata_delta: Dict[str, Any]


class AwaitInput(TypedDict):
    kind: str                     # "interactive_simulate"
    state: str                    # state name
    suggested: AwaitSuggested     # default values from predict_*
    ui_hint: NotRequired[Dict[str, Any]]  # optional UI schema


class ModifiedDecision(TypedDict):
    output: Dict[str, Any]
    ctx_delta: List[Dict[str, Any]]
    metadata_delta: Dict[str, Any]


class InteractiveAdapter:
    """
    Interface for interactive adapters.

    Implementations receive an AwaitInput and must return a ModifiedDecision.
    """
    async def handle(self, await_input: AwaitInput) -> ModifiedDecision:
        raise NotImplementedError
    
    async def truely_execute(self) -> bool:
        return False