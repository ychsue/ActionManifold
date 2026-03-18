# am_core/interactive/adapters.py
import json
from typing import Any

from am_core.interactive.utils import merge_ctx_delta_with_validation, merge_dict_with_validation
from ..types import AwaitInput, ModifiedDecision, InteractiveAdapter


class CLIAdapter(InteractiveAdapter):
    """
    CLI-based interactive adapter.
    User inputs a JSON patch:
        {
            "output": {...},
            "ctx_delta": [...],
            "metadata_delta": {...}
        }
    """
    async def handle(self, await_input: AwaitInput) -> ModifiedDecision:
        state = await_input["state"]
        suggested = await_input["suggested"]
        ui_hint = await_input.get("ui_hint", {})

        print(f"[interactive] state = {state}")
        print(f"[interactive] ui_hint = {ui_hint}")
        print(f"[interactive] suggested = {json.dumps(suggested, indent=2)}")

        raw = input("[interactive] enter JSON patch (blank = keep suggested): ").strip()

        if not raw:
            return ModifiedDecision(
                output=dict(suggested["output"]),
                ctx_delta=list(suggested["ctx_delta"]),
                metadata_delta=dict(suggested["metadata_delta"]),
            )

        try:
            patch = json.loads(raw)
        except Exception as e:
            raise ValueError(f"Invalid JSON: {e}")

        # output
        output = dict(suggested["output"])
        if "output" in patch:
            if not isinstance(patch["output"], dict):
                raise ValueError("output patch must be a dict")
            output = merge_dict_with_validation("output", output, patch["output"])

        # ctx_delta
        ctx_delta = list(suggested["ctx_delta"])
        if "ctx_delta" in patch:
            if not isinstance(patch["ctx_delta"], list):
                raise ValueError("ctx_delta patch must be a list")
            ctx_delta = merge_ctx_delta_with_validation(ctx_delta, patch["ctx_delta"])

        # metadata_delta
        metadata_delta = dict(suggested["metadata_delta"])
        if "metadata_delta" in patch:
            if not isinstance(patch["metadata_delta"], dict):
                raise ValueError("metadata_delta patch must be a dict")
            metadata_delta = merge_dict_with_validation("metadata_delta", metadata_delta, patch["metadata_delta"])

        return ModifiedDecision(
            output=output,
            ctx_delta=ctx_delta,
            metadata_delta=metadata_delta,
        )

    async def truely_execute(self) -> bool:
        print("Do you want to truely execute this decision? (y/N): ", end="")
        choice = input().strip().lower()
        if choice == "y":
            return True
        else:
            return False
