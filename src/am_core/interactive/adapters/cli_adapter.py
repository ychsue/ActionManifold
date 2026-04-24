# am_core/interactive/adapters.py
import asyncio
import json
from typing import Any, Optional, Dict

from am_core.interactive.editor_utils import edit_json_in_editor, read_json_from_stdin
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
    _lock = asyncio.Lock()  # class-level lock to ensure only one CLI prompt at a time

    mode = "auto"  # "auto", "editor", "stdin"

    def _should_use_editor(self):
        if self.mode == "editor":
            return True
        if self.mode == "stdin":
            return False
        # auto
        import sys
        return sys.stdin.isatty()

    def _format_true_execute_message(self, await_input: AwaitInput) -> str:
        state = await_input["state"]
        chain = await_input.get("chain", [])
        ui_hint = await_input.get("ui_hint", {})

        lines = [f"State: {state}"]
        if chain:
            lines.append(f"Chain: {' > '.join(chain)}")

        if ui_hint:
            lines.append("")
            lines.append("UI Hint:")
            lines.append(json.dumps(ui_hint, indent=2, ensure_ascii=False))

        lines.append("")
        lines.append("Do you want to truely execute this decision?")
        return "\n".join(lines)

    def _prompt_true_execute_gui(self, await_input: AwaitInput) -> Optional[bool]:
        try:
            import easygui
        except Exception:
            return None

        state = await_input["state"]
        title = f"Interactive Decision: {state}"
        message = self._format_true_execute_message(await_input)

        try:
            return bool(easygui.ynbox(message, title, choices=("Yes", "No")))
        except Exception:
            return None

    def _prompt_true_execute_cli(self, await_input: AwaitInput) -> bool:
        message = self._format_true_execute_message(await_input)
        print(message)
        print("Choice [y/N]: ", end="")
        choice = input().strip().lower()
        return choice == "y"
    
    async def handle(self, await_input: AwaitInput) -> ModifiedDecision:
        async with self._lock:
            state = await_input["state"]
            suggested = await_input["suggested"]
            ui_hint = await_input.get("ui_hint", {})
    
            print(f"[interactive] state = {state}")
            print(f"[interactive] chain = {json.dumps(await_input.get('chain'), indent=2, ensure_ascii=False)}")
            print(f"[interactive] ui_hint = {ui_hint}")
            print(f"[interactive] suggested = {json.dumps(suggested, indent=2)}")
    
            patch: Optional[Dict[str, Any]] = None
            try:
                if self._should_use_editor():
                    patch = edit_json_in_editor(dict(suggested))
                else:
                    patch = read_json_from_stdin()
    
                if not patch:
                    return ModifiedDecision(
                        output=dict(suggested["output"]),
                        ctx_delta=list(suggested["ctx_delta"]),
                        metadata_delta=dict(suggested["metadata_delta"]),
                    )
    
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

    async def truely_execute(self, await_input: AwaitInput) -> bool:
        if self._should_use_editor():
            gui_choice = self._prompt_true_execute_gui(await_input)
            if gui_choice is not None:
                return gui_choice

        return self._prompt_true_execute_cli(await_input)
